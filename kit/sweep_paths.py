# ============================================================================
# sweep_paths.py - builds the `vi paths` input for pa_exec_state_sweep.xml
# (and pa_cleanup_diagram.xml): every *.vi under a
# folder, each followed by ';', plus a missing path as the negative control.
# The runner cannot set array controls, so the helpers take one ';'-terminated
# string.
# ============================================================================
"""
Usage:  python sweep_paths.py <folder|file.vi> [<folder|file.vi> ...]
                              [--out paths.txt] [--json] [--no-control]
                              [--from N] [--to M] [--check]
  one or more arguments: a folder adds every *.vi under it (recursive, sorted); a
                path ending in .vi adds that file (it must exist). Arguments are
                taken in the order given; a path listed twice is refused.
  --out F       where to write (default paths.txt); `--out -` prints to stdout
  --json        write the inputsJson object {"vi paths": "<...;>"} instead of the
                bare string (what lvai_run_vi_and_read_values takes)
  --check       print the count and the first/last paths, write nothing
  --no-control  leave out the missing-path negative control
  --from N / --to M  keep only VIs N..M-1 of the sorted list (0-based, Python slice)
                before the control is added: batches of ~30 for a long run (F
                Clean Up Diagram, 5 batches over 146 VIs); either may be left out
The control path is <first folder>\\NEGATIVE-CONTROL-missing.vi (for a first
argument that is a .vi: its folder) and must read state 0, error 7.
Written 2026-09-26 (Session D) after three agents rebuilt this list by hand
(Phase 6, icons, cold start). Several arguments, .vi files, --json and `--out -`
added in Session E (ported from the E2 scratch sweep_json.py); with one folder
argument and the old options the output is byte-identical to Session D's.
--from/--to added in the Session F audit (from the F-verify scratch lists.py);
without them the output is unchanged.
"""
import argparse, glob, json, os, sys

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("paths", nargs="+", metavar="folder|file.vi")
ap.add_argument("--out", default="paths.txt")
ap.add_argument("--json", action="store_true")
ap.add_argument("--no-control", action="store_true")
ap.add_argument("--from", dest="from_", type=int, default=None)
ap.add_argument("--to", type=int, default=None)
ap.add_argument("--check", action="store_true")
a = ap.parse_args()

vis = []
first_dir = None
for arg in a.paths:
    p = os.path.abspath(arg)
    if p.lower().endswith(".vi") and not os.path.isdir(p):
        if not os.path.isfile(p):
            sys.exit(f"no such VI: {p}")
        found = [p]
        d = os.path.dirname(p)
    else:
        if not os.path.isdir(p):
            sys.exit(f"not a folder: {p}")
        found = sorted(glob.glob(os.path.join(p, "**", "*.vi"), recursive=True))
        if not found:
            sys.exit(f"no .vi under {p}")
        d = p
    if first_dir is None:
        first_dir = d
    vis += found
seen = set()
for p in vis:
    k = os.path.normcase(p)
    if k in seen:
        sys.exit(f"path listed twice (overlapping arguments?): {p}")
    seen.add(k)
if a.from_ is not None or a.to is not None:
    vis = vis[a.from_:a.to]
    if not vis:
        sys.exit(f"--from {a.from_} --to {a.to} selects no VI")
control =os.path.join(first_dir, "NEGATIVE-CONTROL-missing.vi")
if os.path.exists(control):
    sys.exit(f"the control path exists, it would not be a negative control: {control}")
if not a.no_control:
    vis.append(control)
s = "".join(p + ";" for p in vis)
if a.json:
    s = json.dumps({"vi paths": s})
if a.check:
    print(f"{len(vis)} paths ({len(vis) - (0 if a.no_control else 1)} VIs); first {vis[0]}; last {vis[-1]}")
elif a.out == "-":
    print(s)
else:
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"{len(vis)} paths -> {a.out}")
