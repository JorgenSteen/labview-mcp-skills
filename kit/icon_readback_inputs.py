# ============================================================================
# icon_readback_inputs.py - builds the paired `vi paths` / `png paths` inputs
# for icon_get_vi_icons_n.xml and creates the output folders the PNGs go into
# (Save VI Icon to File writes nothing, and reports no error, into a missing
# folder).
# ============================================================================
"""
Usage:  python icon_readback_inputs.py <out dir> <folder|file.vi> [...] --base <src dir>
                                       [--out inputs.json] [--lists VL PL] [--check]
  <out dir>     root of the read-back tree; each VI goes to
                <out dir>\\<VI path relative to --base, .vi -> .png>
  folder|file.vi  a folder adds every *.vi under it (recursive, sorted); a .vi adds
                that file. Taken in the order given; a VI listed twice is refused.
  --base        the folder the relative PNG paths are taken from (e.g. the project's
                src\\); every VI must lie under it. Use the same base as the reference
                tree so `pixcmp.py --tree <out dir> <reference dir>` pairs them.
  --out F       write the inputsJson there instead of printing it to stdout
  --lists VL PL also write the two bare `;`-terminated lists to the files VL (VI
                paths) and PL (PNG paths): the `vi list` / `png list` inputs of
                icon_get_vi_icons_n_file.xml (from ~100 VIs up). Keep <out dir>
                short: a PNG path over MAX_PATH is written by nobody, code 0 (05
                rule 80)
  --check       print the count, the first pair and the folders it would create;
                create nothing, write nothing
Output: {"vi paths": "a.vi;b.vi;", "png paths": "a.png;b.png;"} - each entry
followed by ';', paired by position, as icon_get_vi_icons_n takes it.

Trailing ';' - which helper takes what (E7/E8 briefs; read from the helper XMLs):
  ACCEPTED by the Match-Pattern loop helpers pa_exec_state_sweep, pa_cleanup_diagram
  and icon_get_vi_icons_n: the loop takes the text before each ';' and stops when the
  rest is empty, so "a;b;" and "a;b" both give two entries (a doubled ";;" gives an
  empty path). REFUSED by icon_apply_icon_and_save_n, which splits with Spreadsheet
  String To Array: a trailing ';' makes an empty last element, an empty path, error 7
  in `open codes`. For that helper strip the final ';' (s.rstrip(';')).
Ported in Session E from the E2 scratch readback_json.py (which had src hard-coded).
--lists added in the Session F audit (the `rb` mode of the F-verify scratch
lists.py); without it the output is unchanged.
"""
import argparse, glob, json, os, sys

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("outdir")
ap.add_argument("paths", nargs="+", metavar="folder|file.vi")
ap.add_argument("--base", required=True)
ap.add_argument("--out")
ap.add_argument("--lists", nargs=2, metavar=("VL", "PL"))
ap.add_argument("--check", action="store_true")
a = ap.parse_args()

base = os.path.abspath(a.base)
outdir = os.path.abspath(a.outdir)
vis = []
for arg in a.paths:
    p = os.path.abspath(arg)
    if p.lower().endswith(".vi") and not os.path.isdir(p):
        if not os.path.isfile(p):
            sys.exit(f"no such VI: {p}")
        vis.append(p)
    elif os.path.isdir(p):
        found = sorted(glob.glob(os.path.join(p, "**", "*.vi"), recursive=True))
        if not found:
            sys.exit(f"no .vi under {p}")
        vis += found
    else:
        sys.exit(f"not a folder or .vi: {p}")
seen = set()
pngs = []
for v in vis:
    k = os.path.normcase(v)
    if k in seen:
        sys.exit(f"VI listed twice (overlapping arguments?): {v}")
    seen.add(k)
    rel = os.path.relpath(v, base)
    if rel.startswith(".."):
        sys.exit(f"VI is not under --base {base}: {v}")
    pngs.append(os.path.join(outdir, rel[:-3] + ".png"))
dirs = sorted({os.path.dirname(p) for p in pngs})
missing = [d for d in dirs if not os.path.isdir(d)]
doc = json.dumps({"vi paths": "".join(v + ";" for v in vis),
                  "png paths": "".join(p + ";" for p in pngs)})
if a.check:
    print(f"{len(vis)} VIs; first {vis[0]} -> {pngs[0]}; "
          f"{len(missing)} of {len(dirs)} output folders would be created; dry run, nothing written")
    for d in missing:
        print("  would create", d)
    sys.exit(0)
for d in missing:
    os.makedirs(d, exist_ok=True)
print(f"{len(vis)} VIs, {len(missing)} folders created", file=sys.stderr)
if a.lists:
    for fn, items in zip(a.lists, (vis, pngs)):
        with open(fn, "w", encoding="utf-8") as f:
            f.write("".join(x + ";" for x in items))
    print(f"{len(vis)} pairs -> {a.lists[0]}, {a.lists[1]}", file=sys.stderr)
if a.out:
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"{len(vis)} pairs -> {a.out}", file=sys.stderr)
else:
    print(doc)
