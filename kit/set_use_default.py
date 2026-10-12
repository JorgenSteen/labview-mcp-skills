# =============================================================================
# set_use_default.py - sets "Use Default if Unwired" on case-structure OUTPUT tunnels that a frame
# leaves unwired, in a pylv_extract bundle (between pylv_extract and pylv_rebuild, project CLOSED).
# =============================================================================
# Why: the right side of a dynamic event registration (Event Structure right terminal -> Unregister,
# made by Connect Wire, kit/pa_wire_dyn_deep.xml) creates a case output tunnel with no value in the
# Error frame, which breaks the VI. VI Server's "Use Default if Unwired" is refused by the AIXML
# property catalogue, so the flag is set in the bundle, in the same round trip as set_user_event_specs.py.
# Measured on an NI accessor (AIXML export `cond="true"`): a use-default output selTun carries objFlags
# 0x300801, a plain one 0x801; LabVIEW itself sets 0x100000 on a tunnel left unwired in a frame. This
# script adds 0x200000 to such tunnels only. Measured 2026-10: cold state 1 with the flag, 0 without.
# It touches EVERY such tunnel in the VI: run --check first and confirm only the expected one is listed.
# usage: set_use_default.py <bundle dir> <base name> [--check]
import io, re, sys

WIRED = 0x8000
USE_DEFAULT = 0x200000


def main(argv):
    check = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print("usage: set_use_default.py <bundle dir> <base name> [--check]")
        sys.exit(2)
    bundle, base = argv[0], argv[1]
    p = "%s/%s_BDHb.xml" % (bundle, base)
    s = io.open(p, encoding="utf-8").read()
    terms = {m.group(1): int(m.group(2)) for m in re.finditer(r'class="term" uid="(\d+)">\s*<objFlags>(\d+)</objFlags>', s)}
    pat = re.compile(r'(<dco class="selTun" uid="(\d+)">\s*<objFlags>)(\d+)(</objFlags>\s*<termList elements="\d+">(.*?)</termList>)', re.S)
    hits = []

    def fix(m):
        flags = int(m.group(3))
        uids = re.findall(r'uid="(\d+)"', m.group(5))
        inner = uids[:-1]
        is_output = (flags & 0xFFF) == 0x801
        unwired = [u for u in inner if not (terms.get(u, 0) & WIRED)]
        if is_output and unwired:
            new = flags | USE_DEFAULT
            hits.append((m.group(2), hex(flags), hex(new), unwired))
            if not check:
                return m.group(1) + str(new) + m.group(4)
        return m.group(0)

    s2 = pat.sub(fix, s)
    for h in hits:
        print("   selTun %s flags %s -> %s (unwired inner terminals %s)" % h)
    print("   %d tunnel(s) %s" % (len(hits), "found" if check else "set"))
    if not check and hits:
        io.open(p, "w", encoding="utf-8", newline="").write(s2)


if __name__ == "__main__":
    main(sys.argv[1:])
