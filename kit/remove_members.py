# =============================================================================
# remove_members.py - removes named member items from a .lvclass or .lvlib by a
# byte-exact edit (BOM and the file's own line ending kept) and, on request, deletes
# the member files they point to. The project must be CLOSED in LabVIEW.
# =============================================================================
"""
Why this exists
    A member made the wrong way (e.g. an accessor generated as dynamic dispatch that has to
    be private, which LabVIEW marks broken) is easiest to drop and make again. Removing it
    in the IDE needs the project open and re-saves the whole class; lvai_* has no "remove
    member" tool. This script removes the member's <Item> block and nothing else.

What it does
    - finds each <Item Name="<member>" Type="..."> at any folder depth (folders excluded)
      and removes its whole block (one-line <Item .../> or open ... </Item>);
    - with --delete-files, deletes the file its URL attribute points to, if it exists.
      The URL is relative to the class/library FILE itself (LabVIEW treats the file as a
      folder level, so `../X.vi` is the VI beside the .lvclass). Fixed in the Session F
      audit (it resolved one folder too high, 05 rule 70). An absolute URL (`/<vilib>/...`)
      is never deleted;
    - leaves every other byte alone, including a virtual folder that becomes empty.

Usage
    python remove_members.py <file.lvclass|file.lvlib> <member> [<member> ...]
                             [--delete-files] [--check]

    <member>        the item's Name attribute, e.g. "Read published_count.vi" (exact)
    --delete-files  also delete the member files from disk
    --check         dry run: print what would be removed/deleted and write nothing.

    Afterwards: lvai_exec_state on the class's remaining members, and check that nothing
    else still calls a removed VI.

Exit code 0 on success, 2 when a member is not found or the file cannot be parsed.
"""
import argparse
import os
import re
import sys

BOM = b"\xef\xbb\xbf"
ITEM = re.compile(rb'^(\t*)<Item Name="([^"]*)" Type="([^"]*)"')
URL = re.compile(rb'\bURL="([^"]*)"')


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("container", help="path of the .lvclass or .lvlib")
    p.add_argument("members", nargs="+", help="Name attribute of each member item (exact)")
    p.add_argument("--delete-files", action="store_true", help="delete the member files too")
    p.add_argument("--check", action="store_true", help="dry run, print the plan, write nothing")
    return p.parse_args(argv)


def unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            .replace("&apos;", "'").replace("&amp;", "&"))


def main(argv=None):
    a = parse_args(argv)
    data = open(a.container, "rb").read()
    bom = data.startswith(BOM)
    body = data[len(BOM):] if bom else data
    nl = b"\r\n" if b"\r\n" in body else b"\n"
    lines = body.split(nl)
    # Item URLs are relative to the FILE that holds them, as if the file were a folder
    # level: `../X.vi` in `C\C.lvclass` is `C\X.vi`. (Until the Session F audit this was
    # the file's folder, one level too high: "no file ...", 05 rule 70.)
    base = os.path.abspath(a.container)

    wanted = set(a.members)
    out, removed, files = [], [], []
    i = 0
    while i < len(lines):
        m = ITEM.match(lines[i])
        if m and m.group(3) != b"Folder" and m.group(2).decode("utf-8") in wanted:
            name = m.group(2).decode("utf-8")
            j = i
            if not lines[i].rstrip().endswith(b"/>"):
                while j < len(lines) and not lines[j].startswith(m.group(1) + b"</Item>"):
                    j += 1
                if j == len(lines):
                    sys.stderr.write("member %r: no closing </Item>\n" % name)
                    return 2
            u = URL.search(lines[i])
            if u and u.group(1).startswith(b"/"):
                print("  %s: URL %s is absolute (vi.lib etc.), its file is never deleted"
                      % (name, u.group(1).decode("utf-8")))
            elif u:
                files.append(os.path.normpath(os.path.join(base, unescape(u.group(1).decode("utf-8")))))
            removed.append(name)
            print("  %s: lines %d-%d" % (name, i + 1, j + 1))
            i = j + 1
            continue
        out.append(lines[i])
        i += 1

    missing = [x for x in a.members if x not in removed]
    if missing:
        sys.stderr.write("members not found: %r\n" % missing)
        return 2
    print("%s%d item(s) | bom %s | line ending %r%s"
          % ("would remove " if a.check else "removed ", len(removed), bom, nl.decode("ascii"),
             " | dry run, nothing written" if a.check else ""))
    if not a.check:
        open(a.container, "wb").write((BOM if bom else b"") + nl.join(out))
    if a.delete_files:
        for f in files:
            if os.path.isfile(f):
                print("  %s %s" % ("would delete" if a.check else "deleted", f))
                if not a.check:
                    os.remove(f)
            else:
                print("  no file %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
