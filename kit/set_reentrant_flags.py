# set_reentrant_flags.py - makes a VI "shared clone reentrant" by setting IsReentrant="1" and
# PooledReentrancy="1" on the <Execution> element of a pylv_extract bundle's main XML, for
# pylv_rebuild afterwards. Needed for a STATIC hook inside a dynamic-dispatch recursion cycle
# (a composite whose hook calls the parent's DD method on its elements): non-reentrant it is
# broken cold (BadNode=1), shared clones make it execState 1 (E4, 05 rule 51). The VI Server route
# ({LV.VI} Execution:Reentrancy Type write + Save.Instrument) validated, ran with no error and
# changed nothing, measured E4.
#
# Usage:  python set_reentrant_flags.py <bundle main .xml> [--off] [--check]
#   --off    set both flags back to "0"
#   --check  print the current flags, write nothing
import re, sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 1:
    sys.exit(__doc__ or "usage: set_reentrant_flags.py <bundle main .xml> [--off] [--check]")
path = args[0]
want = "0" if "--off" in sys.argv else "1"
raw = open(path, "rb").read()
text = raw.decode("utf-8")
m = re.search(r"<Execution [^>]*>", text)
if not m:
    sys.exit("no <Execution ...> element found")
elem = m.group(0)
cur = {k: re.search(k + r'="(\d)"', elem).group(1) for k in ("IsReentrant", "PooledReentrancy")}
print("current:", cur)
if "--check" in sys.argv:
    sys.exit(0)
new = re.sub(r'IsReentrant="\d"', 'IsReentrant="%s"' % want, elem)
new = re.sub(r'PooledReentrancy="\d"', 'PooledReentrancy="%s"' % want, new)
open(path, "wb").write((text[:m.start()] + new + text[m.end():]).encode("utf-8"))
print("written: IsReentrant=%s PooledReentrancy=%s" % (want, want))
