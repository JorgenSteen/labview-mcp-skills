# lvproj_drop.py - remove <Item ...> lines from a .lvproj whose line contains a given substring,
# byte-exact otherwise: the BOM and the file's own line ending (CRLF or LF) are kept.
# Project must be CLOSED in LabVIEW. Writes nothing when nothing matches or when a match
# would remove a structural line (the substring is too broad).
import sys
BOM = b"\xef\xbb\xbf"
STRUCTURAL = (b"<?xml", b"<Project", b"</Project>", b'<Item Name="My Computer"')
if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
    print("usage: python lvproj_drop.py <project .lvproj> <substring>\n"
          "Removes the <Item ...> lines that contain <substring>, byte-exact; project CLOSED.")
    sys.exit(2)
path, needle = sys.argv[1], sys.argv[2].encode("utf-8")
data = open(path, "rb").read()
bom = data.startswith(BOM)
body = data[len(BOM):] if bom else data
nl = b"\r\n" if b"\r\n" in body else b"\n"
lines = body.split(nl)
gone = [l for l in lines if needle in l]
if not gone:
    sys.exit("nothing written: no line contains %r" % needle.decode("utf-8"))
bad = [l for l in gone if l.lstrip().startswith(STRUCTURAL)]
if bad:
    sys.exit("nothing written: the substring matches structural line(s): %s"
             % "; ".join(l.strip().decode("utf-8", "replace")[:80] for l in bad))
kept = [l for l in lines if needle not in l]
open(path, "wb").write((BOM if bom else b"") + nl.join(kept))
print("removed %d line(s), %d -> %d; EOL %s, BOM %s"
      % (len(gone), len(lines), len(kept), "CRLF" if nl == b"\r\n" else "LF", "yes" if bom else "no"))
for l in gone:
    print("  -", l.strip().decode("utf-8", "replace"))
