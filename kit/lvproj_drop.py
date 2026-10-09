# lvproj_drop.py - remove <Item ...> lines from a .lvproj whose line contains a given substring,
# byte-exact otherwise (BOM and CRLF preserved). Project must be CLOSED in LabVIEW.
import sys
path, needle = sys.argv[1], sys.argv[2]
data = open(path, "rb").read()
lines = data.split(b"\r\n")
kept = [l for l in lines if needle.encode("utf-8") not in l]
open(path, "wb").write(b"\r\n".join(kept))
print("removed", len(lines) - len(kept), "line(s); CR count now", b"\r\n".join(kept).count(b"\r"))
