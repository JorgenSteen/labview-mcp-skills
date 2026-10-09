# ============================================================================
# check_membership.py - checks, from the files, that every .vi that sits in a
# folder with a .lvclass or .lvlib is a member item of that class/library (its
# URL resolves to the VI). Read-only; LabVIEW is not called.
# ============================================================================
"""
Why this exists
    A regeneration, a failed convert inside `lvai_add_class_method` (`05` rule 69) or a
    hand edit can leave a VI on disk that is no longer a member, and `execState` of the
    VI alone may still read 1. The F-verify sweep ran this over src\\ (136/136 members).

Usage
    python check_membership.py <folder> [--list-plain] [--check]

    <folder>      the tree to check (e.g. the project's src\\)
    --list-plain  also list the VIs with no .lvclass/.lvlib beside them (launchers,
                  tests, plain VIs); they are counted, never an error
    --check       print how many VIs and owner files it would read; check nothing

What counts as a member
    An owner is every .lvclass (else every .lvlib) in the VI's own folder. A VI is a
    member when some `URL="..."` item of an owner resolves to its path. LabVIEW writes
    item URLs relative to the owner FILE (as if the file were a folder level), so
    `../X.vi` in `C\\C.lvclass` is `C\\X.vi`. `&amp;` etc. are unescaped.

Output: `members checked N  not a member M  no owner (plain VIs) P`, then one
`MISSING <vi>  (owner <file>)` line per non-member. Exit 0 all members, 1 any missing.
Ported in the Session F audit from proof\\PB-F-verify\\membership.py (src hard-coded,
matched by file name only; this version resolves the URL to the full path).
"""
import argparse
import glob
import os
import re
import sys

URL = re.compile(r'\bURL="([^"]+)"')


def unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            .replace("&apos;", "'").replace("&amp;", "&"))


def member_paths(owner):
    txt = open(owner, encoding="utf-8", errors="replace").read()
    out = set()
    for u in URL.findall(txt):
        u = unescape(u)
        if u.startswith("/"):        # /<vilib>/..., absolute: not a local member
            continue
        out.add(os.path.normcase(os.path.normpath(os.path.join(owner, u))))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--list-plain", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.folder)
    if not os.path.isdir(root):
        sys.stderr.write(f"not a folder: {root}\n")
        return 2
    vis = sorted(glob.glob(os.path.join(root, "**", "*.vi"), recursive=True))
    cache = {}
    checked, missing, plain = 0, [], []
    owners_seen = set()
    for vi in vis:
        d = os.path.dirname(vi)
        owners = sorted(glob.glob(os.path.join(d, "*.lvclass"))) or sorted(glob.glob(os.path.join(d, "*.lvlib")))
        if not owners:
            plain.append(vi)
            continue
        owners_seen.update(owners)
        if a.check:
            checked += 1
            continue
        key = os.path.normcase(os.path.normpath(vi))
        hit = False
        for o in owners:
            if o not in cache:
                cache[o] = member_paths(o)
            if key in cache[o]:
                hit = True
                break
        checked += 1
        if not hit:
            missing.append((vi, ", ".join(os.path.basename(o) for o in owners)))
    if a.check:
        print(f"{len(vis)} VIs under {root}: {checked} beside {len(owners_seen)} owner files, "
              f"{len(plain)} plain; dry run, nothing checked")
        return 0
    print("members checked", checked, "not a member", len(missing), "no owner (plain VIs)", len(plain))
    for vi, o in missing:
        print("  MISSING", os.path.relpath(vi, root), " (owner " + o + ")")
    if a.list_plain:
        for p in plain:
            print("  plain", os.path.relpath(p, root))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
