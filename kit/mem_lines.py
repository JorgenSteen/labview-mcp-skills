# =============================================================================
# mem_lines.py - prints the "lines" of a saved pa_project_vis_modified answer (the answer can exceed the
# tool-result limit on a large project, and is then saved to a file by the harness).
# =============================================================================
"""Usage: python mem_lines.py <saved answer .txt> <out .txt> [filter ...]
Writes every line to <out>; prints the lines that are modified (fp/bd/vi != 0) or match a filter."""
import json, re, sys, html

src, out = sys.argv[1], sys.argv[2]
filters = sys.argv[3:]
raw = open(src, encoding="utf-8").read()
data = json.loads(raw)
if isinstance(data, list):
    data = json.loads(data[0]["text"])
xml = data["values"]["lines"]["xml"]
vals = [html.unescape(v) for v in re.findall(r"<Val>(.*?)</Val>", xml, re.S)]
open(out, "w", encoding="utf-8").write("\n".join(vals) + "\n")
print("in memory:", len(vals))
for v in vals:
    f = v.split("\t")
    mod = len(f) > 3 and (f[0] != "0" or f[1] != "0" or f[2] != "0")
    if mod or any(x.lower() in v.lower() for x in filters):
        print(("MOD " if mod else "    ") + v)
