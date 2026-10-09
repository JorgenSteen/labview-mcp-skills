# ==========================================================================================
# lv_loadability.py - offline check whether LabVIEW code will load: per VI/class/library,
# "loadable" or the dependencies that do not resolve and the load chain that reaches them,
# so a session never loads code that stops LabVIEW on a modal "Find the VI" dialog.
# ==========================================================================================
"""Usage:
  python lv_loadability.py <target> [<target> ...] [--search <root> ...] [--vilib <vi.lib>]
                           [--lazy] [--json] [--all] [--links]
  python lv_loadability.py --check

What it does
  Reads files only; LabVIEW is not called. For each target it builds the load closure: a VI
  loads every file its link info names (the first path of each link entry in the LI* blocks)
  and its owning library; a class loads its members, its parents and its owning library; a
  library loads its owning library and (default model) the classes and libraries it contains.
  Each link is resolved against the file itself (relative paths), the LabVIEW install (vi.lib,
  user.lib, instr.lib, resource) and the search roots. A file that is missing at its saved path
  but has a unique name in the search roots or in the LabVIEW install counts as found
  ("relocated": LabVIEW finds it by name). Class private data typedefs are read too (the
  embedded control in NI.LVClass.FlattenedPrivateDataCTL).

Targets
  a .vi/.ctl/.vim/.vit/.ctt, a .lvclass/.lvlib/.lvsc/.xctl, a .lvproj (each of its items), or a
  folder: every class and library under it, plus every VI/control that no library under it owns
  (members are checked through their class or library).

Options
  --search <root>  where LabVIEW may find a moved file by name (repeatable). Default: the
                   nearest folder at or above the first target holding .git or .labview, else
                   the target's own folder.
  --vilib <path>   the vi.lib of the LabVIEW that will load the code (or that LabVIEW's folder).
                   Default: the only LabVIEW install under Program Files; with several, exit 2.
  --lazy           a library loads only its own file, not the classes/libraries it contains
                   (the lower bound; the default model loads them, which LabVIEW usually does).
  --json           one JSON document instead of text.
  --all            list loadable targets too (text mode lists only unresolved ones and a count).
  --links          print each target VI's resolved links instead (one VI's dependency list).
  --check          offline self-test on built-in samples; reads no file.

Exit: 0 every target resolves; 1 something does not resolve; 2 usage error.
Limits: what is unresolved, not which call will show a dialog (some load paths only mark the
VI broken). Conditional-disable frames and dynamic calls (by path or name at run time) are not
seen. A package missing on purpose (an RT or FPGA target's code on a desktop LabVIEW) reads as
unresolved: say so in the report rather than installing anything.
Provenance: ported from the skills audit's offline closure (audit run G: about 5 s for 5800
files; it predicted every LabVIEW hang of the audit).
"""
import base64
import collections
import json
import os
import re
import struct
import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import unquote

VIEXT = (".vi", ".ctl", ".vim", ".vit", ".ctt")
LIBEXT = (".lvclass", ".lvlib", ".lvsc", ".xctl")
CONTAINER = (".lvclass", ".lvlib", ".lvsc", ".xctl", ".llb", ".lvlibp") + VIEXT
SYM = {"<vilib>": "vi.lib", "<userlib>": "user.lib", "<instrlib>": "instr.lib", "<resource>": "resource",
       "<menus>": "menus", "<help>": "help", "<examples>": "examples", "<lvroot>": ""}
LVSUBS = ("vi.lib", "user.lib", "instr.lib", "resource")
IDENT = re.compile(rb"\x00\x02([A-Z][A-Za-z]{3})\x00\x00")

# Well-known packages a link may need: (regex over the link path, name). Fallback: the path head.
PACKAGES = [
    (r"_JKI\.lib/Serialization/JSON|JKI JSON", "JKI JSON Serialization (VIPM)"),
    (r"_OpenG\.lib", "OpenG Toolkit (VIPM)"),
    (r"_JKI", "JKI toolkit (VIPM)"),
    (r"Model Interface Toolkit", "NI Model Interface Toolkit (VeriStand)"),
    (r"niSync", "NI-Sync LabVIEW API (instr.lib/niSync)"),
    (r"IEDriver", "NI FPGA SPI/I2C IP (vi.lib/IEDriver)"),
    (r"/rvi/|FPGAPlugInAG|LabVIEW Targets/FPGA|/eio/|niFpga|\.lvbitx", "LabVIEW FPGA Module"),
    (r"nisyscfg|objmgr/ni(controller)?sysapi", "NI System Configuration API (nisyscfg)"),
    (r"RT Get CPU Loads|RT CPU Load|rtutility\.llb|NI_Real-Time Target Support", "LabVIEW Real-Time Module"),
    (r"_office|NIReport\.llb", "Report Generation Toolkit"),
]


def key(p):
    return os.path.normcase(os.path.normpath(p))


# ---------------------------------------------------------------- RSRC and link info
def rsrc_blocks(b):
    """Raw sections of each named block of a LabVIEW RSRC image (bytes)."""
    if b[:4] != b"RSRC":
        return {}
    rsrc_off, _rsize, data_off, _dsize = struct.unpack(">IIII", b[16:32])
    p = rsrc_off + 32
    _a, _b, _c, bi_off, _bi_size = struct.unpack(">IIIII", b[p:p + 20])
    q = rsrc_off + bi_off
    n = struct.unpack(">I", b[q:q + 4])[0] + 1
    out = {}
    for i in range(n):
        e = q + 4 + i * 12
        name = b[e:e + 4].decode("latin1")
        cnt, off = struct.unpack(">II", b[e + 4:e + 12])
        secs = []
        for s in range(cnt + 1):
            so = q + off + s * 20
            _idx, _noff, _i3, doff, _i4 = struct.unpack(">iIIII", b[so:so + 20])
            dp = data_off + doff
            size = struct.unpack(">I", b[dp:dp + 4])[0]
            secs.append(b[dp + 4:dp + 4 + size])
        out[name] = secs
    return out


def link_bytes(image):
    res = b""
    try:
        for k, secs in rsrc_blocks(image).items():
            if k.startswith("LI"):
                res += b"".join(secs)
    except (struct.error, IndexError):
        pass
    return res


def parse_paths(data):
    """(kind, [components]) of the first PTH0/PTH1 path of each link entry. Later paths in the same
    entry are auxiliary (e.g. a stale absolute path of a parent class) and are not needed to load it."""
    out = []
    idents = [m.start() for m in IDENT.finditer(data)]
    last = None
    j = 0
    for m in re.finditer(rb"PTH[01]", data):
        p = m.start()
        while j < len(idents) and idents[j] < p:
            j += 1
        cur = idents[j - 1] if j else -1
        if cur == last:
            continue
        last = cur
        try:
            if data[p:p + 4] == b"PTH0":
                tot = struct.unpack(">I", data[p + 4:p + 8])[0]
                tp, n = struct.unpack(">HH", data[p + 8:p + 12])
                q = p + 12
                comps = []
                for _ in range(n):
                    ln = data[q]
                    comps.append(data[q + 1:q + 1 + ln].decode("latin1"))
                    q += 1 + ln
                if q - (p + 8) != tot:
                    continue
                out.append(({0: "abs", 1: "rel"}.get(tp, str(tp)), comps))
            else:
                tot = struct.unpack(">I", data[p + 4:p + 8])[0]
                tp = data[p + 8:p + 12].decode("latin1").strip()
                q = p + 12
                comps = []
                while q < p + 8 + tot:
                    ln = struct.unpack(">H", data[q:q + 2])[0]
                    comps.append(data[q + 2:q + 2 + ln].decode("latin1"))
                    q += 2 + ln
                out.append((tp, comps))
        except (struct.error, IndexError):
            continue
    return out


_B64 = bytes.maketrans(bytes(range(33, 97)),
                       b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
_NOT6 = bytes(i for i in range(256) if not 33 <= i < 97)


def lv_unflatten(text):
    """LabVIEW's 6-bit text encoding of a Bin property ('!' = 0, big-endian 6-bit groups) -> bytes."""
    v = text.encode("latin1", "ignore").translate(_B64, _NOT6)
    v = v[:len(v) - 1] if len(v) % 4 == 1 else v
    return base64.b64decode(v + b"=" * (-len(v) % 4))


# ---------------------------------------------------------------- the checker
class Checker:
    def __init__(self, lvroot, roots, strict):
        self.lvroot = lvroot
        self.lvkey = key(lvroot) + os.sep if lvroot else None
        self.roots = roots
        self.strict = strict
        self.nodes = {}
        self.tree_idx = collections.defaultdict(list)  # basename -> paths under the search roots
        self.libs = []
        self._lv_idx = None
        self._llb = {}
        self.owner = {}
        self.path_of, self.sum_of, self.comp_sum = {}, {}, []
        self.succ, self._rev, self._dist = {}, None, {}
        self.file_bits, self.miss_bits, self.rel_bits, self.bit_items = {}, {}, {}, {}
        for r in roots:
            for dp, dn, fn in os.walk(r):
                dn[:] = [d for d in dn if d not in (".git", ".labview", "__pycache__")]
                for f in fn:
                    lo = f.lower()
                    if lo.endswith(VIEXT + LIBEXT):
                        p = os.path.normpath(os.path.join(dp, f))
                        self.tree_idx[lo].append(p)
                        if lo.endswith(LIBEXT):
                            self.libs.append(p)
        for lib in self.libs:  # owner map: member -> owning class/library
            for m in self.node(lib)["members"]:
                self.owner.setdefault(key(m), lib)

    # -- indexes
    def lv_idx(self):
        if self._lv_idx is None:
            self._lv_idx = collections.defaultdict(list)
            if self.lvroot:
                for sub in LVSUBS:
                    for dp, dn, fn in os.walk(os.path.join(self.lvroot, sub)):
                        for f in fn:
                            self._lv_idx[f.lower()].append(os.path.join(dp, f))
        return self._lv_idx

    def in_lv(self, p):
        return bool(self.lvkey) and key(p).startswith(self.lvkey)

    def llb_has(self, llb, name):
        k = key(llb)
        if k not in self._llb:
            try:
                with open(llb, "rb") as f:
                    self._llb[k] = f.read()
            except OSError:
                self._llb[k] = b""
        return name.encode("latin1", "replace") in self._llb[k]

    # -- resolving one link
    def resolve(self, src, kind, comps):
        """-> (path, label) or (None, '')"""
        if not comps:
            return None, ""
        if comps[0] in SYM:
            if not self.lvroot:
                return None, comps[0]
            return os.path.normpath(os.path.join(self.lvroot, SYM[comps[0]], *comps[1:])), comps[0]
        if kind.startswith("abs"):
            if len(comps[0]) == 1 or comps[0].endswith(":"):
                return os.path.normpath(comps[0].rstrip(":") + ":\\" + "\\".join(comps[1:])), "abs"
            return None, ""
        cur = src  # relative to the file itself: each '' strips one level
        for c in comps:
            cur = os.path.dirname(cur) if c == "" else os.path.join(cur, c)
        return os.path.normpath(cur), "rel"

    def classify(self, target, label, comps):
        """-> ('lv'|'file'|'relocated'|'relocated_file'|'missing', path or description)"""
        if os.path.isfile(target):
            return ("lv" if self.in_lv(target) else "file"), target
        parts = target.split(os.sep)
        low = [x.lower() for x in parts]
        if label == "rel" and self.lvroot:  # a relative path that climbed into another LabVIEW's tree
            for d, sym in (("vi.lib", "<vilib>"), ("user.lib", "<userlib>"), ("instr.lib", "<instrlib>")):
                if d in low:
                    i = low.index(d)
                    comps = [sym] + parts[i + 1:]
                    target = os.path.join(self.lvroot, d, *parts[i + 1:])
                    label = sym
                    if os.path.isfile(target):
                        return "lv", target
                    break
        for i in range(len(parts) - 1, 0, -1):  # a member inside a container file
            if parts[i - 1].lower().endswith(CONTAINER):
                cont = os.sep.join(parts[:i])
                if os.path.isfile(cont):
                    if cont.lower().endswith((".llb", ".lvlibp")):
                        if self.llb_has(cont, parts[i]):
                            return ("lv" if self.in_lv(cont) else "file_leaf"), cont
                        break
                    return ("lv" if self.in_lv(cont) else "file"), cont
                target = cont
                break
        base = os.path.basename(target).lower()
        if label in SYM:
            hits = self.lv_idx().get(base, [])
            if len(hits) == 1:
                return "relocated", hits[0]
            return "missing", label + "/" + "/".join(comps[1:])
        hits = self.tree_idx.get(base, [])
        if len(hits) == 1:
            return "relocated_file", hits[0]
        hits = self.lv_idx().get(base, [])
        if len(hits) == 1:
            return "relocated", hits[0]
        return "missing", self.show(target) + ("  [absolute link]" if label == "abs" else "")

    def show(self, p):
        for r in self.roots:
            k = key(r) + os.sep
            if key(p).startswith(k):
                return os.path.relpath(p, r).replace("\\", "/")
        return p.replace("\\", "/")

    def add_link(self, node, src, kind, comps, note=""):
        t, lab = self.resolve(src, kind, comps)
        if t is None:
            if lab:
                node["missing"].append(lab + "/" + "/".join(comps[1:]) + note)
            return None
        st, v = self.classify(t, lab, comps)
        if st == "missing":
            node["missing"].append(v + note)
            return None
        if st in ("relocated", "relocated_file"):
            node["relocated"].append((self.show(t), self.show(v)))
        if st in ("file", "relocated_file") and key(v) != key(src):
            node["links"].append(v)
            return v
        return None

    # -- one file's node
    def node(self, p):
        k = key(p)
        n = self.nodes.get(k)
        if n is not None:
            return n
        n = {"path": p, "kind": os.path.splitext(p)[1].lower(), "links": [], "missing": [], "relocated": [],
             "members": [], "parents": [], "childlibs": [], "err": ""}
        self.nodes[k] = n
        if n["kind"] in VIEXT:
            try:
                with open(p, "rb") as f:
                    data = link_bytes(f.read())
            except OSError as e:
                n["err"] = str(e)
                data = b""
            for kind, comps in parse_paths(data):
                self.add_link(n, p, kind, comps)
        elif n["kind"] in LIBEXT + (".lvproj",):
            self.parse_lib(p, n)
        return n

    def parse_lib(self, p, n):
        try:
            root = ET.parse(p).getroot()
        except (ET.ParseError, OSError) as e:
            n["err"] = str(e)
            return
        for pr in root.iter("Property"):
            name = pr.get("Name")
            if name == "NI.Lib.ContainingLibPath" and pr.text:
                t = os.path.normpath(os.path.join(p, unquote(pr.text)))
                st, v = self.classify(t, "rel", [])
                if st == "missing":
                    n["missing"].append(v + "  [owning library]")
                elif st in ("file", "relocated_file"):
                    n["links"].append(v)
            elif name == "NI.LVClass.FlattenedPrivateDataCTL" and pr.text:
                blob = lv_unflatten(pr.text)
                i = blob.find(b"RSRC")
                if i >= 0:
                    ctl = os.path.join(p, os.path.splitext(os.path.basename(p))[0] + ".ctl")
                    for kind, comps in parse_paths(link_bytes(blob[i:])):
                        self.add_link(n, ctl, kind, comps, "  [private data]")
        skip = set()
        for it in root.iter("Item"):
            if it.get("Name") == "Dependencies" or it.get("Type") == "Build":
                skip.update(id(x) for x in it.iter("Item"))
        for it in root.iter("Item"):
            if id(it) in skip:
                continue
            u, typ = it.get("URL"), it.get("Type") or ""
            if not u or "Friend" in typ or typ == "Class Private Data":
                continue
            u = unquote(u)
            m = re.match(r"/(<[a-z]+>)(.*)", u)
            if m:
                comps = [m.group(1)] + [c for c in m.group(2).split("/") if c]
                t, lab = self.resolve(p, "abs", comps)
            elif re.match(r"/[A-Za-z]/", u):
                comps = []
                t, lab = os.path.normpath(u[1] + ":\\" + u[3:]), "abs"
            else:
                comps = []
                t, lab = os.path.normpath(os.path.join(p, u)), "rel"
            if t is None:
                continue
            if os.path.isdir(t):
                if n["kind"] == ".lvproj":
                    n["members"].append(t)
                continue
            st, v = self.classify(t, lab, comps)
            if st == "missing":
                n["missing"].append(v + ("  [parent]" if typ == "Parent" else "  [item " + typ + "]"))
                continue
            if st in ("relocated", "relocated_file"):
                n["relocated"].append((self.show(t), self.show(v)))
            if typ == "Parent":
                n["parents"].append(v)
                continue
            n["members"].append(v)
            if typ in ("LVClass", "Library", "Interface", "XControl", "LVLibp", "StateChart"):
                n["childlibs"].append(v)

    # -- the closure
    def edges(self, p):
        n = self.node(p)
        e = list(n["links"])
        o = self.owner.get(key(p))
        if o:
            e.append(o)
        if n["kind"] == ".lvclass":
            e += n["members"] + n["parents"]
        elif n["kind"] in (".lvlib", ".lvsc", ".xctl") and self.strict:
            e += n["childlibs"]
        return [x for x in e if not self.in_lv(x) and os.path.isfile(x)
                and x.lower().endswith(VIEXT + LIBEXT)]

    def summarise(self, starts):
        """Closure of every node reachable from starts, as bitsets: files, missing entries, relocated
        links. Strongly connected components (Tarjan, iterative) are folded once, in reverse
        topological order, so a large tree costs one pass instead of one walk per target."""
        idx, low, comp_of = {}, {}, {}
        stack, on, comps = [], set(), []
        succ = self.succ
        counter = 0
        for s0 in starts:
            k0 = key(s0)
            if k0 in idx:
                continue
            work = [(s0, 0)]
            while work:
                p, i = work[-1]
                k = key(p)
                if i == 0 and k not in idx:
                    idx[k] = low[k] = counter
                    counter += 1
                    stack.append(k)
                    on.add(k)
                    succ[k] = [(key(q), q) for q in self.edges(p)]
                    self.path_of[k] = p
                sl = succ[k]
                if i < len(sl):
                    work[-1] = (p, i + 1)
                    kq, q = sl[i]
                    if kq not in idx:
                        work.append((q, 0))
                    elif kq in on:
                        low[k] = min(low[k], idx[kq])
                    continue
                work.pop()
                if work:
                    kp = key(work[-1][0])
                    low[kp] = min(low[kp], low[k])
                if low[k] == idx[k]:
                    members = []
                    while True:
                        x = stack.pop()
                        on.discard(x)
                        comp_of[x] = len(comps)
                        members.append(x)
                        if x == k:
                            break
                    comps.append(members)
        for c, members in enumerate(comps):  # successors come first in Tarjan's order
            files = miss = rel = 0
            for k in members:
                n = self.nodes[k]
                files |= 1 << self.bit(self.file_bits, k)
                for m in n["missing"]:
                    miss |= 1 << self.bit(self.miss_bits, m)
                for r in n["relocated"]:
                    rel |= 1 << self.bit(self.rel_bits, r)
                for kq, _q in succ[k]:
                    cq = comp_of[kq]
                    if cq != c:
                        f2, m2, r2 = self.comp_sum[cq]
                        files |= f2
                        miss |= m2
                        rel |= r2
            self.comp_sum.append((files, miss, rel))
            for k in members:
                self.sum_of[k] = len(self.comp_sum) - 1

    def bit(self, table, item):
        i = table.get(item)
        if i is None:
            i = table[item] = len(table)
            self.bit_items.setdefault(id(table), []).append(item)
        return i

    def decode(self, table, bits):
        items = self.bit_items.get(id(table), [])
        out, i = [], 0
        while bits:
            if bits & 1:
                out.append(items[i])
            bits >>= 1
            i += 1
        return out

    def result(self, start):
        """(closure size, missing entries, relocated links) of one node, after summarise()."""
        files, miss, rel = self.comp_sum[self.sum_of[key(start)]]
        return bin(files).count("1"), self.decode(self.miss_bits, miss), self.decode(self.rel_bits, rel)

    def dist(self, pk):
        """Per file: the fewest load steps to a file that links an entry of package pk (reverse BFS)."""
        if pk in self._dist:
            return self._dist[pk]
        if self._rev is None:
            self._rev = collections.defaultdict(list)
            for k, sl in self.succ.items():
                for kq, _q in sl:
                    self._rev[kq].append(k)
        d = {}
        dq = collections.deque()
        for k in self.succ:
            if any(package(m) == pk for m in self.nodes[k]["missing"]):
                d[k] = 0
                dq.append(k)
        while dq:
            k = dq.popleft()
            for kp in self._rev.get(k, ()):
                if kp not in d:
                    d[kp] = d[k] + 1
                    dq.append(kp)
        self._dist[pk] = d
        return d

    def chains(self, start, wanted):
        """Shortest load chain from start to a file that links an entry of each wanted package."""
        out = {}
        for pk in wanted:
            d = self.dist(pk)
            k = key(start)
            if k not in d:
                continue
            ch = [k]
            while d[k] > 0:
                k = next(kq for kq, _q in self.succ[k] if d.get(kq) == d[k] - 1)
                ch.append(k)
            m = next(m for m in self.nodes[k]["missing"] if package(m) == pk)
            out[pk] = [self.show(self.path_of[x]) for x in ch] + [m.split("  [")[0]]
        return out


def package(entry):
    """The package (or kind of gap) a missing entry belongs to; notes after two spaces are ignored."""
    if "  [absolute link]" in entry:
        return "missing absolute path"
    e = entry.split("  [")[0].replace("\\", "/")
    for rx, name in PACKAGES:
        if re.search(rx, e, re.I):
            return name
    if e.startswith("<"):
        c = e.split("/")
        n = 3 if len(c) > 2 and c[1].lower() == "addons" else 2
        return "/".join(c[:n])
    return "missing in the code itself"


# ---------------------------------------------------------------- targets
def find_lvroot(vilib):
    if vilib:
        v = os.path.normpath(vilib)
        if os.path.basename(v).lower() != "vi.lib" and os.path.isdir(os.path.join(v, "vi.lib")):
            v = os.path.join(v, "vi.lib")
        if not os.path.isdir(v):
            return None, "no such vi.lib folder: " + vilib
        return os.path.dirname(v), ""
    found = []
    for pf in {os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""),
               os.environ.get("ProgramW6432", "")}:
        ni = os.path.join(pf, "National Instruments") if pf else ""
        if ni and os.path.isdir(ni):
            for d in os.listdir(ni):
                if d.lower().startswith("labview 20") and os.path.isdir(os.path.join(ni, d, "vi.lib")):
                    found.append(os.path.join(ni, d))
    if len(found) == 1:
        return found[0], ""
    return None, ("several LabVIEW installs; pass --vilib <LabVIEW>\\vi.lib of the one that loads the code:\n  "
                  + "\n  ".join(sorted(found)) if found else "no LabVIEW install found; pass --vilib")


def default_root(target):
    d = target if os.path.isdir(target) else os.path.dirname(target)
    d = os.path.abspath(d)
    cur = d
    while True:
        if os.path.exists(os.path.join(cur, ".git")) or os.path.isdir(os.path.join(cur, ".labview")):
            return cur
        up = os.path.dirname(cur)
        if up == cur:
            return d
        cur = up


def expand(ck, target):
    t = os.path.abspath(target)
    lo = t.lower()
    if os.path.isdir(t):
        libs, loose = [], []
        for dp, dn, fn in os.walk(t):
            dn[:] = [d for d in dn if d not in (".git", ".labview", "__pycache__")]
            for f in sorted(fn):
                p = os.path.normpath(os.path.join(dp, f))
                if f.lower().endswith(LIBEXT):
                    libs.append(p)
                elif f.lower().endswith(VIEXT):
                    loose.append(p)
        owned = set()
        for lib in libs:
            owned.update(key(m) for m in ck.node(lib)["members"])
        return sorted(libs) + sorted(p for p in loose if key(p) not in owned and key(p) not in ck.owner)
    if lo.endswith(".lvproj"):
        out = []
        for m in ck.node(t)["members"]:
            out += expand(ck, m) if os.path.isdir(m) else [m]
        return out
    if lo.endswith(VIEXT + LIBEXT):
        return [os.path.normpath(t)]
    return None


# ---------------------------------------------------------------- self-test
def check():
    ok = True
    comps = [b"", b"Common", b"x.vi"]
    body = struct.pack(">HH", 1, len(comps)) + b"".join(bytes([len(c)]) + c for c in comps)
    data = b"\x00\x02VIVI\x00\x00" + b"PTH0" + struct.pack(">I", len(body)) + body
    data += b"PTH0" + struct.pack(">I", len(body)) + body  # second path of the same entry: ignored
    got = parse_paths(data)
    ok &= got == [("rel", ["", "Common", "x.vi"])]
    ck = Checker.__new__(Checker)
    ck.lvroot, ck.lvkey = r"C:\LV", key(r"C:\LV") + os.sep
    r, lab = ck.resolve(r"C:\p\a\b.vi", "rel", ["", "", "Common", "x.vi"])
    ok &= (r, lab) == (os.path.normpath(r"C:\p\Common\x.vi"), "rel")
    r, lab = ck.resolve(r"C:\p\a\b.vi", "abs", ["<vilib>", "Utility", "error.llb", "Clear Errors.vi"])
    ok &= r == os.path.normpath(r"C:\LV\vi.lib\Utility\error.llb\Clear Errors.vi") and lab == "<vilib>"
    ok &= lv_unflatten("!!!!") == b"\x00\x00\x00"
    ok &= package("<userlib>/_OpenG.lib/file/file.llb/Create Dir.vi") == "OpenG Toolkit (VIPM)"
    ok &= package("<vilib>/addons/Foo/x.vi") == "<vilib>/addons/Foo"
    ok &= package("src/Common/x.vi  [parent]") == "missing in the code itself"
    ok &= package("C:/old/x.vi  [absolute link]") == "missing absolute path"
    print("check", "ok" if ok else "FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------- main
def main(argv):
    if argv[:1] == ["--check"]:
        return check()
    targets, roots, vilib, flags = [], [], None, set()
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--search", "--vilib"):
            if i + 1 >= len(argv):
                print("missing value for " + a, file=sys.stderr)
                return 2
            if a == "--search":
                roots.append(os.path.abspath(argv[i + 1]))
            else:
                vilib = argv[i + 1]
            i += 2
            continue
        if a in ("--lazy", "--json", "--all", "--links"):
            flags.add(a)
        elif a.startswith("--"):
            print(__doc__, file=sys.stderr)
            return 2
        else:
            targets.append(a)
        i += 1
    if not targets:
        print(__doc__, file=sys.stderr)
        return 2
    for t in targets:
        if not os.path.exists(t):
            print("no such target: " + t, file=sys.stderr)
            return 2
    for r in roots:
        if not os.path.isdir(r):
            print("no such search root: " + r, file=sys.stderr)
            return 2
    lvroot, err = find_lvroot(vilib)
    if lvroot is None:
        print(err, file=sys.stderr)
        return 2
    roots = roots or [default_root(targets[0])]
    t0 = time.time()
    ck = Checker(lvroot, roots, "--lazy" not in flags)
    todo = []
    for t in targets:
        e = expand(ck, t)
        if e is None:
            print("not a LabVIEW file or folder: " + t, file=sys.stderr)
            return 2
        todo += e

    if "--links" in flags:
        for p in todo:
            n = ck.node(p)
            print(ck.show(p))
            for x in dict.fromkeys(x for x in n["links"] if key(x) != key(p)):
                print("  link     ", ck.show(x))
            for a, b in n["relocated"]:
                print("  relocated", a, "->", b)
            for m in n["missing"]:
                print("  MISSING  ", m)
        return 1 if any(ck.node(p)["missing"] for p in todo) else 0

    ck.summarise(todo)
    results = []
    for p in todo:
        size, miss, reloc = ck.result(p)
        pk = collections.OrderedDict()
        for m in miss:
            pk.setdefault(package(m), []).append(m)
        ch = ck.chains(p, set(pk)) if pk else {}
        results.append({"target": ck.show(p), "kind": os.path.splitext(p)[1].lower(),
                        "loadable": not miss, "closure_files": size,
                        "unresolved": [{"package": k, "entries": sorted(v), "chain": ch.get(k, [])}
                                       for k, v in pk.items()],
                        "relocated": sorted(reloc)})
    secs = round(time.time() - t0, 2)
    bad = [r for r in results if not r["loadable"]]
    meta = {"labview": lvroot, "search_roots": roots, "model": "lazy" if "--lazy" in flags else "strict",
            "targets": len(results), "unresolved_targets": len(bad), "files_read": len(ck.nodes), "seconds": secs}
    if "--json" in flags:
        json.dump({"meta": meta, "results": results}, sys.stdout, indent=1)
        print()
        return 1 if bad else 0

    print("LabVIEW %s | search %s | model %s" % (lvroot, "; ".join(roots), meta["model"]))
    for r in results:
        if r["loadable"]:
            if "--all" in flags:
                print("LOADABLE    %s  (%d files)" % (r["target"], r["closure_files"]))
            continue
        print("UNRESOLVED  %s  (%d files)" % (r["target"], r["closure_files"]))
        for u in r["unresolved"]:
            print("    %s: %d unresolved, e.g. %s" % (u["package"], len(u["entries"]), u["entries"][0]))
            print("      chain: " + " > ".join(os.path.basename(x.rstrip("/")) for x in u["chain"]))
    per_pk = collections.Counter(u["package"] for r in bad for u in r["unresolved"])
    nrel = len({x for r in results for x in r["relocated"]})
    print("targets %d: loadable %d, unresolved %d; files read %d; %.2f s"
          % (len(results), len(results) - len(bad), len(bad), len(ck.nodes), secs))
    for k, v in per_pk.most_common():
        print("  %4d targets need %s" % (v, k))
    if nrel:
        print("  %d links found only by file name (LabVIEW searches for them; --json lists them)" % nrel)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
