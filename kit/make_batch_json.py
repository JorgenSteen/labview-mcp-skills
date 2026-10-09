# =============================================================================
# make_batch_json.py - turns a small table file into the batch JSON of two tools:
# `methods` -> methodsJson for lvai_add_class_method, `edits` -> editsJson for
# lvai_swap_subvis. Read-only: it prints (or writes with --out) the JSON, nothing else.
# =============================================================================
r"""
Why this exists
    A class with a dozen hooks needs lvai_add_class_method batches (every method with its
    classTerminals, some with a {"terminal","class"} entry for another class) and a series
    of lvai_swap_subvis batches (socket -> real VI, seed constant -> class). Typed by hand,
    the JSON is long, full of escaped Windows paths and easy to get wrong; the ROOT build
    (Session D) used two scratch scripts for it 2x and 6x. This is their generic form: the
    names live in a table, not in the script.

The tools' JSON (from their own schema descriptions, labview-mcp 1.8.0)
    methodsJson  [{"aixml": <.xml>, "vi": <.vi>, "classTerminals": [<name> | {"terminal":
                  <name>, "class": <.lvclass>}], "dispatchTerminals": [<name>]}]
                  A bare name = the method's own class. No dispatchTerminals = STATIC method
                  (it is left out of the JSON, as the tool wants: an empty value is refused).
    editsJson    [{"vi": <.vi>, "swaps": [{"socket": <stub VI name>, "target": <.vi>}],
                  "constants": [{"label": <constant label>, "class": <.lvclass>}]}]
                  Nodes are swapped first, constants last. EVERY SOCKET NAME MUST BE UNIQUE
                  within one VI's swaps (the tool refuses a name given twice), and a batch
                  STOPS at the first VI that answers ok:false.

THE SHARED-STUB TRAP (05 rule 38)
    One placeholder stub used by two nodes of one VI (e.g. the same stub in two Case frames)
    needs one swap call per node, and "newest node first" is NOT reliable across Case
    frames. So give such a VI one row per node, each in its own `batch` (pass), run the
    passes in order, export after the first one and check which node it hit; a wrong
    placement is re-swapped by using the real VI's qualified name as the socket. --check
    warns when a VI with a repeated socket shares a pass with other VIs (after its first
    pass it answers ok:false, and the batch would stop there).

Table formats (by file extension)
    CSV, first line = header, one row per terminal list / per swap:
      methods:  batch,vi,aixml,classTerminals,dispatchTerminals
                classTerminals / dispatchTerminals: names separated by ';';
                a terminal of ANOTHER class is written  name=<path to .lvclass>
      edits:    batch,vi,kind,name,path
                kind = swap (name = socket, path = target VI) or constant (name = label,
                path = .lvclass). Rows of one vi in one batch are merged into one entry, in
                file order; VIs keep the order of their first row.
    JSON: {"vars": {...}, "rows": [ {same keys as the CSV columns} ]}; in JSON,
          classTerminals / dispatchTerminals may also be real lists.

    In both formats:
      ${NAME}         is replaced by a variable from the JSON "vars" block or --var NAME=value
                      (paths: keep folders in variables, so rows stay short);
      stub:<id>       as a socket name means  "LVMCP Stub <id>.vi"  (lvai_placeholder_subvi's
                      spelling); any other socket name is used as written;
      batch           any label; empty = "1". Rows with '#' as the first character are skipped.

    Example (edits.csv):
        batch,vi,kind,name,path
        main,${CF}\Foo-launch.vi,swap,stub:22edf158c0,${CF}\Read output_folder.vi
        main,${CF}\Foo-launch.vi,constant,cm seed,${CM}\Foo-CM.lvclass
        p1,${CF}\Foo-init.vi,swap,stub:5b720fe284,${CF}\Foo-launch_hwm.vi
        p2,${CF}\Foo-init.vi,swap,stub:5b720fe284,${CF}\Foo-launch_cm.vi
    Example (methods.csv):
        batch,vi,aixml,classTerminals,dispatchTerminals
        1,${CF}\Foo-stop.vi,${CF}\Foo-stop.xml,Foo in,
        2,${CF}\X-handle.vi,${CF}\X-handle.xml,Foo in;Foo out;package=${PKG}\P.lvclass,Foo in;Foo out

Usage
    python make_batch_json.py methods <table> [--batch B] [--var N=V ...] [--out F] [--check]
    python make_batch_json.py edits   <table> [--batch B] [--var N=V ...] [--out F] [--check]

    --batch B   emit that batch; required when the table has more than one.
    --out F     write the JSON to F (UTF-8, no BOM) instead of printing it.
    --check     validate the table and print every batch that would be emitted; write nothing.

Exit code 0 on success, 2 on a table error (the message names the row).
"""
import argparse
import csv
import json
import os
import re
import sys

VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
COLUMNS = {"methods": ["batch", "vi", "aixml", "classTerminals", "dispatchTerminals"],
           "edits": ["batch", "vi", "kind", "name", "path"]}


class TableError(Exception):
    pass


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["methods", "edits"])
    p.add_argument("table", help="the table file (.csv or .json)")
    p.add_argument("--batch", help="the batch to emit")
    p.add_argument("--var", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument("--out", help="write the JSON here instead of stdout")
    p.add_argument("--check", action="store_true", help="validate, print every batch, write nothing")
    return p.parse_args(argv)


def load(path, mode, cli_vars):
    variables = {}
    if path.lower().endswith(".json"):
        doc = json.load(open(path, encoding="utf-8-sig"))
        variables.update(doc.get("vars", {}))
        rows = doc.get("rows", [])
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f)]
        missing = [c for c in COLUMNS[mode] if rows and c not in rows[0]]
        if missing:
            raise TableError("CSV header lacks column(s) %s (need %s)" % (missing, ",".join(COLUMNS[mode])))
    for kv in cli_vars:
        if "=" not in kv:
            raise TableError("--var %r: expected NAME=VALUE" % kv)
        k, v = kv.split("=", 1)
        variables[k] = v
    out = []
    for n, r in enumerate(rows, start=2 if not path.lower().endswith(".json") else 1):
        first = str(next(iter(r.values()), "") or "")
        if first.startswith("#"):
            continue
        out.append((n, {k: expand(v, variables, n) for k, v in r.items() if k is not None}))
    return out


def expand(v, variables, n):
    if isinstance(v, list):
        return [expand(x, variables, n) for x in v]
    if isinstance(v, dict):
        return {k: expand(x, variables, n) for k, x in v.items()}
    if v is None:
        return ""
    def sub(m):
        if m.group(1) not in variables:
            raise TableError("row %d: variable ${%s} is not defined" % (n, m.group(1)))
        return variables[m.group(1)]
    return VAR.sub(sub, str(v)).strip()


def split_terms(v):
    if isinstance(v, list):
        return v
    return [t.strip() for t in v.split(";") if t.strip()] if v else []


def term_entry(t, n, warn):
    if isinstance(t, dict):
        name, cls = t.get("terminal", ""), t.get("class", "")
    elif "=" in t:
        name, cls = [x.strip() for x in t.split("=", 1)]
    else:
        return t
    if not name or not cls.lower().endswith(".lvclass"):
        raise TableError("row %d: terminal entry %r needs a name and a .lvclass path" % (n, t))
    if not os.path.isfile(cls):
        warn.append("row %d: class file not found: %s" % (n, cls))
    return {"terminal": name, "class": cls}


def build_methods(rows, warn):
    batches = {}
    for n, r in rows:
        b = r.get("batch") or "1"
        vi, aixml = r.get("vi", ""), r.get("aixml", "")
        if not vi and not aixml:
            raise TableError("row %d: needs vi and/or aixml" % n)
        terms = [term_entry(t, n, warn) for t in split_terms(r.get("classTerminals", ""))]
        if not terms:
            raise TableError("row %d: classTerminals is empty" % n)
        names = [t["terminal"] if isinstance(t, dict) else t for t in terms]
        disp = split_terms(r.get("dispatchTerminals", ""))
        bad = [d for d in disp if d not in names]
        if bad:
            raise TableError("row %d: dispatchTerminals %s are not in classTerminals" % (n, bad))
        if aixml and not os.path.isfile(aixml):
            warn.append("row %d: aixml not found (yet): %s" % (n, aixml))
        m = {}
        if aixml:
            m["aixml"] = aixml
        if vi:
            m["vi"] = vi
        m["classTerminals"] = terms
        if disp:
            m["dispatchTerminals"] = disp
        vis = [x.get("vi") for x in batches.get(b, [])]
        if vi and vi in vis:
            raise TableError("row %d: vi given twice in batch %s: %s" % (n, b, vi))
        batches.setdefault(b, []).append(m)
    return batches


def build_edits(rows, warn):
    batches, seen_socket = {}, {}
    for n, r in rows:
        b = r.get("batch") or "1"
        vi, kind, name, path = r.get("vi", ""), r.get("kind", "").lower(), r.get("name", ""), r.get("path", "")
        if not vi or not name or not path:
            raise TableError("row %d: vi, name and path are required" % n)
        entries = batches.setdefault(b, [])
        e = next((x for x in entries if x["vi"] == vi), None)
        if e is None:
            e = {"vi": vi, "swaps": [], "constants": []}
            entries.append(e)
        if kind == "swap":
            socket = "LVMCP Stub %s.vi" % name[5:].strip() if name.startswith("stub:") else name
            if any(s["socket"] == socket for s in e["swaps"]):
                raise TableError("row %d: socket %r given twice for %s in batch %s: the tool refuses "
                                 "a repeated socket; put the second node in a later batch (05 rule 38)"
                                 % (n, socket, os.path.basename(vi), b))
            if not path.lower().endswith((".vi", ".vim")):
                raise TableError("row %d: swap target is not a .vi: %s" % (n, path))
            e["swaps"].append({"socket": socket, "target": path})
            seen_socket.setdefault((vi, socket), []).append(b)
        elif kind == "constant":
            if any(c["label"] == name for c in e["constants"]):
                raise TableError("row %d: constant label %r given twice for %s in batch %s" % (n, name, vi, b))
            if not path.lower().endswith(".lvclass"):
                raise TableError("row %d: constant class is not a .lvclass: %s" % (n, path))
            e["constants"].append({"label": name, "class": path})
        else:
            raise TableError("row %d: kind must be swap or constant, not %r" % (n, kind))
        if not os.path.isfile(path):
            warn.append("row %d: file not found: %s" % (n, path))
    for (vi, socket), bs in seen_socket.items():
        if len(bs) > 1:
            for b in bs:
                if len(batches[b]) > 1:
                    warn.append("%s: socket %s is swapped in batches %s (shared stub); in batch %s it shares "
                                "the call with %d other VI(s) - a VI with a node left answers ok:false and "
                                "stops the batch; run it alone or last, export after the first pass (05 rule 38)"
                                % (os.path.basename(vi), socket, ",".join(bs), b, len(batches[b]) - 1))
    return batches


def main(argv=None):
    a = parse_args(argv)
    warn = []
    try:
        rows = load(a.table, a.mode, a.var)
        if not rows:
            raise TableError("the table has no rows")
        batches = (build_methods if a.mode == "methods" else build_edits)(rows, warn)
        if a.batch is not None and a.batch not in batches:
            raise TableError("batch %r not in the table (have: %s)" % (a.batch, ", ".join(batches)))
        if not a.check and a.batch is None and len(batches) > 1:
            raise TableError("the table has %d batches (%s): choose one with --batch"
                             % (len(batches), ", ".join(batches)))
    except (TableError, OSError, ValueError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    for w in warn:
        print("WARNING: %s" % w, file=sys.stderr)
    if a.check:
        for b, items in batches.items():
            if a.batch is not None and b != a.batch:
                continue
            print("batch %s: %d %s" % (b, len(items), "method(s)" if a.mode == "methods" else "VI(s)"))
            print(json.dumps(items))
        print("check only, nothing written", file=sys.stderr)
        return 0
    text = json.dumps(batches[a.batch if a.batch is not None else next(iter(batches))])
    if a.out:
        open(a.out, "w", encoding="utf-8", newline="").write(text)
        print("written %s (%d bytes)" % (a.out, len(text.encode("utf-8"))), file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
