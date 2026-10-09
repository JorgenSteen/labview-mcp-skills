# ============================================================================
# aixml_frames.py - prints each <Call> (and <Node>) of an AIXML export with
# the Case frames (and structures) around it, outermost first, so you can see
# which frame a shared-stub swap landed in (05 rule 38). Read-only.
# ============================================================================
"""
Usage:  python aixml_frames.py <export.xml> [--calls] [--grep TEXT] [--check]
  --calls      only <Call> elements (subVI calls), no primitive <Node>s
  --grep TEXT  only lines whose callee/name contains TEXT (case-insensitive),
               e.g. a stub name "LVMCP Stub" or the swapped VI's name
  --check      print only the element counts, nothing per line (read-only anyway)
One line per element:  <frame path> :: <callee or node name>
  frame path = the enclosing structures, outermost first, joined by " / ": a Case
  frame prints as its selector (e.g. "Launch Nested"), any other structure as
  <its _name> (e.g. <While Loop>); "(root)" = directly on the diagram.
Why: `lvai_swap_subvis` on a stub shared by several Case frames does not reliably
hit the newest node (05 rule 38), so export the VI after each swap
(lvai_convert_vi_to_aixml) and check with this script. Ported in Session E from
the E5 scratch frames.py.
"""
import argparse, sys
import xml.etree.ElementTree as ET

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("xml")
ap.add_argument("--calls", action="store_true")
ap.add_argument("--grep")
ap.add_argument("--check", action="store_true")
a = ap.parse_args()

rows = []


def walk(el, path):
    for ch in el:
        if ch.tag == "CaseFrame":
            walk(ch, path + [ch.get("selector") or "?"])
        elif ch.tag == "Structure":
            walk(ch, path + ["<" + (ch.get("_name") or "") + ">"])
        elif ch.tag in ("Call", "Node"):
            if ch.tag == "Node" and a.calls:
                continue
            name = (ch.get("target") if ch.tag == "Call" else ch.get("_name")) or ""
            rows.append((ch.tag, " / ".join(path) or "(root)", name))
        else:
            walk(ch, path)


walk(ET.parse(a.xml).getroot(), [])
if a.grep:
    rows = [r for r in rows if a.grep.lower() in r[2].lower()]
if a.check:
    calls = sum(1 for r in rows if r[0] == "Call")
    print(f"{len(rows)} elements ({calls} Call, {len(rows) - calls} Node) in {a.xml}")
    sys.exit(0)
for _, path, name in rows:
    print(path, "::", name)
