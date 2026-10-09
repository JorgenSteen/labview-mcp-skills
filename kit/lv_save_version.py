# ==========================================================================================
# lv_save_version.py - report which LabVIEW version a .vi/.ctl/.vim (binary) or a
# .lvclass/.lvlib/.lvproj (XML) was last saved in, on disk or at a git revision, so a
# session can prove whether a LabVIEW call silently re-saved (upgraded) a foreign file.
# ==========================================================================================
# Used by the save-version route (knowledge/labview-mcp.md, "Save version"): scan before the
# first save, re-scan after the step. Portable: no project names, every path is an argument.
# Provenance: ported from the skills audit's scratch scanners (audit runs L2, L3, L4, L7).
#
# Usage:
#   python lv_save_version.py [--repo <git repo>] [--rev <rev>|WT] <file> [<file> ...]
#   python lv_save_version.py --check
# Paths are relative to --repo when --repo is given (needed for --rev), else as given.
# Output, one line per file:  <rev> <bytes> <major>  <evidence>  <name>
#   binary: counts of the BCD version stamp "<major> <minor|fix> 80 00" per major, e.g. 20:5
#   XML:    the LVVersion / NI.LV.All.SaveVersion attribute values
# The binary scan is a HEURISTIC (it reads stamps, not the parsed 'vers' resource); it was
# validated in the audit against files saved by LabVIEW 2020 and 2026 (L2, L3, L7).
# Exit code: 0 ok, 1 a file was missing, 2 usage.
import re
import subprocess
import sys

STAMP = re.compile(rb"([\x08-\x30])([\x00-\x99])\x80\x00")
XMLVER = re.compile(rb'(LVVersion="(\d+)"|NI\.LV\.All\.SaveVersion"[^>]*>([\d.]+)<)')
XML_EXT = (".lvclass", ".lvlib", ".lvproj", ".xctl", ".lvsc")


def bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


def scan(name, data):
    """Return (major or '?', evidence) for one file's bytes."""
    if name.lower().endswith(XML_EXT):
        vals = []
        for m in XMLVER.finditer(data):
            if m.group(2):
                vals.append("LVVersion=" + m.group(2).decode())
            elif m.group(3):
                vals.append("SaveVersion=" + m.group(3).decode())
        major = "?"
        for v in vals:
            if v.startswith("LVVersion="):
                major = str(int(v.split("=")[1][:2]))
                break
        return major, ",".join(sorted(set(vals))) or "no version attribute"
    counts = {}
    for m in STAMP.finditer(data):
        b0 = m.group(1)[0]
        major = bcd(b0)
        if (b0 & 0x0F) <= 9 and 8 <= major <= 30:
            counts[major] = counts.get(major, 0) + 1
    if not counts:
        return "?", "no stamp"
    top = max(counts, key=counts.get)
    return str(top), " ".join(f"{k}:{counts[k]}" for k in sorted(counts))


def read(repo, rev, path):
    if rev == "WT":
        full = path if not repo else repo.rstrip("/\\") + "/" + path
        try:
            with open(full, "rb") as f:
                return f.read()
        except OSError:
            return None
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def check():
    ok = True
    v20 = b"RSRC" + b"\x00" * 40 + b"\x20\x00\x80\x00" * 3 + b"\x26\x00\x80\x00"
    ok &= scan("a.vi", v20) == ("20", "20:3 26:1")
    ok &= scan("b.vi", b"\x26\x01\x80\x00" * 2) == ("26", "26:2")
    ok &= scan("c.ctl", b"plain bytes") == ("?", "no stamp")
    x = b'<Library LVVersion="26008000"><Property Name="NI.LV.All.SaveVersion" Type="Str">20.0</Property>'
    ok &= scan("d.lvclass", x) == ("26", "LVVersion=26008000,SaveVersion=20.0")
    ok &= scan("e.lvlib", b"<Library>") == ("?", "no version attribute")
    print("check", "ok" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if argv[:1] == ["--check"]:
        return check()
    repo, rev, files = "", "WT", []
    i = 0
    while i < len(argv):
        if argv[i] == "--repo" and i + 1 < len(argv):
            repo = argv[i + 1]; i += 2
        elif argv[i] == "--rev" and i + 1 < len(argv):
            rev = argv[i + 1]; i += 2
        else:
            files.append(argv[i]); i += 1
    if not files or (rev != "WT" and not repo):
        print("usage: python lv_save_version.py [--repo <git repo>] [--rev <rev>|WT] <file> [<file> ...]\n"
              "       python lv_save_version.py --check", file=sys.stderr)
        return 2
    missing = 0
    for p in files:
        data = read(repo, rev, p)
        name = p.replace("\\", "/").split("/")[-1]
        if data is None:
            print(f"{rev:8} missing {p}")
            missing += 1
            continue
        major, ev = scan(name, data)
        print(f"{rev:8} {len(data):7} {major:>2}  {ev:28} {name}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
