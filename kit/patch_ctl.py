# patch_ctl.py - turn a pylv_extract bundle of a generated VI into a typedef control:
# <Instrument Type="Standard"> -> "Control", TypeDefVI="0" -> "1" (anchored so StrictTypeDefVI is untouched).
import re, sys
for p in sys.argv[1:]:
    s = open(p, encoding="utf-8").read()
    s, n1 = re.subn(r'<Instrument Type="Standard"', '<Instrument Type="Control"', s)
    s, n2 = re.subn(r'(?<!Strict)TypeDefVI="0"', 'TypeDefVI="1"', s)
    open(p, "w", encoding="utf-8").write(s)
    print(p, "instrument:", n1, "typedef:", n2)
