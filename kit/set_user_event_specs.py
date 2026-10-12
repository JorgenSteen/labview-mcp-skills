# set_user_event_specs.py - writes an Event Structure's USER-EVENT EventSpecs with an explicit dynIndex.
# Why: lvai_wire_dynamic_events refuses to finish a VI with more than one user-event frame, and
# pylv-set-event-spec.py documents "--user-event <Name> [dynIndex]" but its main() ignores dynIndex
# (always 1). Measured in M3: dynIndex = the event source's 1-based position on Register For Events.
# Route: lvai_generate_vi_with_events -> lvai_wire_dynamic_events (wire made, finish refused) ->
#        close project -> pylv_extract -> THIS -> pylv_rebuild -> exec_state/export.
# usage: set_user_event_specs.py <bundle dir> <base name> <diagramIdx>:<name>:<dynIndex> [...] [--check]
#        --check only prints the current EventSpec rows. Bundle files are edited in place (utf-8, newline kept).
import glob, importlib.util, io, os, re, sys


def find_script():
    pat = os.path.expanduser(r"~\.claude\plugins\cache\zuehlke-labview\labview-mcp\*\bin\scripts\pylv-set-event-spec.py")
    hits = sorted(glob.glob(pat))
    if not hits:
        raise SystemExit("pylv-set-event-spec.py not found under " + pat)
    return hits[-1]


def rows(path):
    s = io.open(path, encoding="utf-8").read()
    for m in re.finditer(r'<SL__arrayElement class="EventSpec">(.*?)</SL__arrayElement>', s, re.S):
        blk = m.group(1)
        get = lambda t: (re.search(r"<%s>(-?\d+)</%s>" % (t, t), blk) or [None, "?"])[1]
        print("   diagramIdx %s source %s type %s dynIndex %s" % (get("diagramIdx"), get("source"), get("type"), get("dynIndex")))


def main(argv):
    check = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print("usage: set_user_event_specs.py <bundle dir> <base name> <diagramIdx>:<name>:<dynIndex> [...] [--check]\n"
              "       --check only prints the current EventSpec rows.")
        sys.exit(2)
    bundle, base, specs = argv[0], argv[1], argv[2:]
    p = "%s/%s_BDHb.xml" % (bundle, base)
    if check:
        rows(p)
        return
    spec = importlib.util.spec_from_file_location("setspec", find_script())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for item in specs:
        idx, name, dyn = item.split(":")
        mod.main(bundle, base, idx, "--user-event", name)
        s = io.open(p, encoding="utf-8").read()
        pat = re.compile(r'(<SL__arrayElement class="EventSpec">\s*<diagramIdx>%s</diagramIdx>.*?<dynIndex>)(\d+)(</dynIndex>)' % idx, re.S)
        s, n = pat.subn(lambda m: m.group(1) + dyn + m.group(3), s, count=1)
        assert n == 1, "dynIndex of frame %s not found" % idx
        io.open(p, "w", encoding="utf-8", newline="").write(s)
        print("   frame %s dynIndex -> %s" % (idx, dyn))
    rows(p)


if __name__ == "__main__":
    main(sys.argv[1:])
