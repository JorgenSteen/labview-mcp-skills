# =============================================================================
# read_saved_answer.py - reads a large labview-mcp tool answer that Claude Code saved
# to a file (too big for the tool-result limit) and prints a compact summary, filtered
# by name. Knows lvai_describe_project, lvai_placeholder_subvi, lvai_add_class_method.
# =============================================================================
"""
Why this exists
    lvai_describe_project, lvai_placeholder_subvi and lvai_add_class_method answers are
    40-90 kB; Claude Code writes them to ...\\tool-results\\<name>.txt and returns only the
    path. Reading that file whole floods the context. This prints the few lines needed.

Input forms accepted
    - the tool's JSON answer as saved (a dict);
    - the MCP content wrapper [{"type": "text", "text": "<json>"}];
    - lvai_describe_project's stream form {"messages": [{"infoJson": "<json string>"}]}:
      infoJson is decoded and each message's project is shown.

What it prints
    describe_project   per target: libraries and classes (name, item count), top-level VIs.
                       With --name: the items of every matching library/class, in LabVIEW's
                       order, as  type  scope  name  (virtual folders show as "Directory";
                       the list is flat, the folder's members follow it).
    placeholder_subvi  per subject VI: ok, placeholder stub name, class terminals, and with
                       --call the <Call .../> element to author against.
    add_class_method   ok, counts, failedAtStep; per method: ok, verifiedOnDisk,
                       terminalsRetyped, and every step with its errorCode if any.
    anything else      the top-level keys and scalar values.
    --grep TEXT prints every JSON path whose key or scalar value contains TEXT (any form).

Usage
    python read_saved_answer.py <saved file> [--name SUBSTR] [--call] [--grep TEXT] [--json PATH]

    --name SUBSTR   only libraries/classes/VIs/methods whose name contains SUBSTR
    --call          placeholder_subvi: also print each <Call .../> element
    --grep TEXT     print the matching paths and values instead of the summary
    --json PATH     print the JSON subtree at a dotted path, e.g. methods.0.steps.1.answer

Read-only; writes nothing.
"""
import argparse
import json
import sys


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", help="saved tool answer (.txt/.json)")
    p.add_argument("--name", help="filter by name substring (case-insensitive)")
    p.add_argument("--call", action="store_true", help="placeholder_subvi: print the <Call/> elements")
    p.add_argument("--grep", help="print JSON paths whose key or value contains this text")
    p.add_argument("--json", dest="path", help="print the subtree at a dotted path")
    return p.parse_args(argv)


def load(path):
    raw = open(path, encoding="utf-8-sig", errors="replace").read()
    obj = json.loads(raw)
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and obj[0].get("type") == "text":
        obj = json.loads("".join(x.get("text", "") for x in obj if x.get("type") == "text"))
    if isinstance(obj, dict) and isinstance(obj.get("messages"), list):
        infos = []
        for msg in obj["messages"]:
            if isinstance(msg, dict) and isinstance(msg.get("infoJson"), str):
                infos.append(json.loads(msg["infoJson"]))
        if infos:
            return infos[0] if len(infos) == 1 else {"projects": infos}
    return obj


def hit(name, flt):
    return flt is None or flt.lower() in (name or "").lower()


def show_project(p, flt):
    print("PROJECT %s  (%s)" % (p.get("projectName"), p.get("projectPath")))
    if p.get("errorCode"):
        print("  errorCode %s %s" % (p.get("errorCode"), p.get("errorMessage")))
    for t in p.get("targets", []):
        libs = [(l, "LIBRARY") for l in t.get("libraries", [])]
        libs += [(c["library"], "INTERFACE" if c.get("interface") else "CLASS") for c in t.get("classes", [])]
        print("TARGET %s: %d libraries, %d classes, %d VIs"
              % (t.get("targetName"), len(t.get("libraries", [])), len(t.get("classes", [])), len(t.get("vis", []))))
        for lib, kind in libs:
            name = lib.get("libraryName", "")
            if not hit(name, flt):
                continue
            extra = []
            if lib.get("missingItems"):
                extra.append("%d MISSING" % len(lib["missingItems"]))
            if lib.get("parent"):
                extra.append("parent " + lib["parent"])
            print("  %-9s %s  (%d items%s)" % (kind, name, len(lib.get("items", [])),
                                              ", " + ", ".join(extra) if extra else ""))
            if flt is not None:
                for it in lib.get("items", []):
                    print("      %-28s %-14s %s" % (it.get("type", ""), it.get("scope", ""), it.get("name", "")))
                for it in lib.get("missingItems", []):
                    print("      MISSING %s" % (it if not isinstance(it, dict) else it.get("name", it)))
        for vi in t.get("vis", []):
            if hit(vi.get("name"), flt):
                print("  VI        %s" % vi.get("name"))
        for f in t.get("missingFiles", []):
            print("  MISSING   %s" % f)


def show_placeholders(obj, flt, call):
    print("placeholder_subvi ok %s | requested %s | failed %s" % (obj.get("ok"), obj.get("requested"), obj.get("failed")))
    for p in obj.get("placeholders", []):
        vi = p.get("viPath", "")
        if not hit(vi, flt):
            continue
        a = p.get("answer") or {}
        print("  %s" % vi.replace("\\", "/").rsplit("/", 1)[-1])
        print("      ok %s | stub %s | reused %s | class terminals %s"
              % (a.get("ok"), a.get("placeholder"), a.get("reused"), a.get("classTerminalNames")))
        if not a.get("ok"):
            print("      note %s" % (a.get("note") or "")[:300])
        if call and a.get("call"):
            print("      %s" % a["call"])
    if obj.get("note"):
        print("note: %s" % obj["note"][:400])


def show_methods(obj, flt):
    print("add_class_method ok %s | %s | asked %s added %s | failedAtStep %s"
          % (obj.get("ok"), obj.get("lvclassPath"), obj.get("methodsAsked"), obj.get("methodsAdded"),
             obj.get("failedAtStep")))
    for m in obj.get("methods", []):
        if not hit(m.get("method"), flt):
            continue
        print("  %s: ok %s | verifiedOnDisk %s | terminalsRetyped %s | dynamicDispatch %s | existed %s"
              % (m.get("method"), m.get("ok"), m.get("verifiedOnDisk"), m.get("terminalsRetyped"),
                 m.get("dynamicDispatchTerminals"), m.get("memberAlreadyExisted")))
        for s in m.get("steps", []):
            ans = s.get("answer") if isinstance(s.get("answer"), dict) else {}
            err = ans.get("errorCode") or ans.get("helperErrorCode")
            print("      %-8s %s%s" % (s.get("step"), "ok" if ans.get("ok", not err) else "NOT OK",
                                       " errorCode %s %s" % (err, (ans.get("errorMessage") or "")[:160]) if err else ""))
    if obj.get("note"):
        print("note: %s" % obj["note"][:400])


def show_generic(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                print("  %s: %s[%d]" % (k, type(v).__name__, len(v)))
            else:
                print("  %s: %s" % (k, str(v)[:200]))
    else:
        print("  %s[%d]" % (type(obj).__name__, len(obj)))


def grep(obj, text, path=""):
    t = text.lower()
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = "%s.%s" % (path, k) if path else str(k)
            if not isinstance(v, (dict, list)) and (t in str(k).lower() or t in str(v).lower()):
                print("%s = %s" % (p, str(v)[:300]))
            else:
                grep(v, text, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = "%s.%d" % (path, i) if path else str(i)
            if not isinstance(v, (dict, list)):
                if t in str(v).lower():
                    print("%s = %s" % (p, str(v)[:300]))
            else:
                grep(v, text, p)


def subtree(obj, path):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def main(argv=None):
    a = parse_args(argv)
    try:
        obj = load(a.file)
    except ValueError as e:
        sys.stderr.write("%s is not a saved JSON tool answer (%s); use grep on it instead\n" % (a.file, e))
        return 2
    if a.path:
        print(json.dumps(subtree(obj, a.path), indent=2, ensure_ascii=False)[:20000])
    elif a.grep:
        grep(obj, a.grep)
    elif isinstance(obj, dict) and "targets" in obj:
        show_project(obj, a.name)
    elif isinstance(obj, dict) and "projects" in obj:
        for p in obj["projects"]:
            show_project(p, a.name)
    elif isinstance(obj, dict) and "placeholders" in obj:
        show_placeholders(obj, a.name, a.call)
    elif isinstance(obj, dict) and "methods" in obj and "lvclassPath" in obj:
        show_methods(obj, a.name)
    else:
        show_generic(obj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
