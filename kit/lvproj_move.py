# =============================================================================
# lvproj_move.py - moves ONE one-line <Item .../> of a .lvproj into a named virtual
# folder that is its sibling (same parent, e.g. both directly under "My Computer"),
# byte-exact otherwise: the BOM and the file's own line ending (CRLF or LF) are kept.
# The project must be CLOSED in LabVIEW.
# =============================================================================
"""
Why this exists
    The writing tools (lvai_add_vis_to_project, lvai_add_to_library, the library helper)
    drop a new project item directly under "My Computer". The project's virtual folders
    (common, hardware, protocol, tests, ...) are the reviewer's map of the project, and a
    LabVIEW re-save of the .lvproj to move one item rewrites the whole file. This script
    moves the one item, with the project closed, and changes nothing else.

What it does
    - finds the folder line  <tabs><Item Name="<folder>" Type="Folder">  (or the empty form
      ... Type="Folder"/>, which is expanded to an open/close pair);
    - finds the one-line item  <tabs><Item Name="<item>" .../>  at the SAME depth as the
      folder (a sibling; the Name attribute must match exactly);
    - re-inserts it one tab deeper inside the folder, in case-insensitive name order among
      the folder's own one-line children. Item URLs are relative to the .lvproj file, not
      to the folder, so the line itself does not change.

    With --create (Session E, E7: ported from the scratch lvproj_add_folder.py) the folder
    must NOT exist yet: it is created as a sibling of the item (same parent, same depth), in
    case-insensitive name order among the parent's other folders (before the first folder
    whose name sorts after it, else after the last folder's closing tag, else where the item
    stood), and the item becomes its only child. A folder of that name anywhere in the file
    is refused (nothing written): drop --create to move into it.

Usage
    python lvproj_move.py <project.lvproj> <item name> <folder name> [--create] [--check]

    --create    make the folder first (it must not exist); see above.
    --check     dry run: print what would move where and write nothing.

Exit code 0 on success, non-zero with a message when the item or folder is not found once
(or, with --create, when the folder already exists).
"""
import argparse
import re
import sys

BOM = b"\xef\xbb\xbf"
ITEM = re.compile(rb'^(\t*)<Item Name="([^"]*)"')


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lvproj", help="path of the project file (.lvproj)")
    p.add_argument("item", help="Name attribute of the one-line item to move (exact)")
    p.add_argument("folder", help="Name attribute of the target virtual folder (exact)")
    p.add_argument("--create", action="store_true",
                   help="create the folder (must not exist) as the item's sibling, then move")
    p.add_argument("--check", action="store_true", help="dry run, print the plan, write nothing")
    return p.parse_args(argv)


def name_of(line):
    m = ITEM.match(line)
    return m.group(2).decode("utf-8") if m else None


def depth_of(line):
    m = ITEM.match(line)
    return len(m.group(1)) if m else None


def main(argv=None):
    a = parse_args(argv)
    data = open(a.lvproj, "rb").read()
    bom = data.startswith(BOM)
    body = data[len(BOM):] if bom else data
    nl = b"\r\n" if b"\r\n" in body else b"\n"
    lines = body.split(nl)

    if a.create:
        return create_and_move(a, lines, bom, nl)

    folders = [i for i, ln in enumerate(lines)
               if name_of(ln) == a.folder and re.search(rb'\bType="Folder"', ln)]
    if len(folders) != 1:
        sys.exit("folder %r: %d matches (need exactly 1)" % (a.folder, len(folders)))
    fi = folders[0]
    fdepth = depth_of(lines[fi])
    ftabs = b"\t" * fdepth

    items = [i for i, ln in enumerate(lines) if name_of(ln) == a.item]
    if not items:
        sys.exit("item %r: not found" % a.item)
    siblings = [i for i in items if depth_of(lines[i]) == fdepth]
    if len(siblings) != 1:
        where = ", ".join("line %d (depth %d)" % (i + 1, depth_of(lines[i])) for i in items)
        sys.exit("item %r: %d at the folder's depth %d (need exactly 1); found at %s"
                 % (a.item, len(siblings), fdepth, where))
    si = siblings[0]
    item = lines[si]
    if not item.rstrip().endswith(b"/>"):
        sys.exit("item %r at line %d is not a one-line element" % (a.item, si + 1))

    # remove the item; the folder index shifts if the item stood above it
    lines.pop(si)
    if si < fi:
        fi -= 1

    # expand an empty folder  <Item Name="x" Type="Folder"/>  into open + close lines
    if lines[fi].rstrip().endswith(b"/>"):
        lines[fi] = lines[fi].rstrip()[:-2] + b">"
        lines.insert(fi + 1, ftabs + b"</Item>")

    # insert in case-insensitive name order among the folder's one-line children
    j = fi + 1
    key = a.item.lower()
    while (lines[j].startswith(ftabs + b"\t<Item ") and lines[j].rstrip().endswith(b"/>")
           and (name_of(lines[j]) or "").lower() < key):
        j += 1
    lines.insert(j, b"\t" + item)

    print("%s%r (line %d) -> folder %r, new line %d | bom %s | line ending %r%s"
          % ("would move " if a.check else "moved ", a.item, si + 1, a.folder, j + 1, bom,
             nl.decode("ascii"), " | dry run, nothing written" if a.check else ""))
    if not a.check:
        open(a.lvproj, "wb").write((BOM if bom else b"") + nl.join(lines))
    return 0


def create_and_move(a, lines, bom, nl):
    """--create: make a new sibling folder of the item and move the item into it."""
    if re.search(r'[<>&"]', a.folder):
        sys.exit("folder name %r: characters < > & \" are not allowed" % a.folder)
    dup = [i for i, ln in enumerate(lines)
           if name_of(ln) == a.folder and re.search(rb'\bType="Folder"', ln)]
    if dup:
        sys.exit("folder %r exists already (line %d): nothing written; drop --create to move into it"
                 % (a.folder, dup[0] + 1))
    items = [i for i, ln in enumerate(lines)
             if name_of(ln) == a.item and ln.rstrip().endswith(b"/>")]
    if len(items) != 1:
        sys.exit("item %r: %d one-line matches (need exactly 1)" % (a.item, len(items)))
    si = items[0]
    depth = depth_of(lines[si])
    tabs = b"\t" * depth
    if depth == 0:
        sys.exit("item %r at line %d has no parent item" % (a.item, si + 1))
    # the parent: the nearest open <Item ...> line above at depth - 1, closed by </Item> at that depth
    pi = si - 1
    while pi >= 0 and not (depth_of(lines[pi]) == depth - 1 and not lines[pi].rstrip().endswith(b"/>")):
        pi -= 1
    if pi < 0:
        sys.exit("item %r: parent not found" % a.item)
    pe = pi + 1
    while pe < len(lines) and lines[pe].rstrip() != b"\t" * (depth - 1) + b"</Item>":
        pe += 1
    item = lines.pop(si)
    pe -= 1

    # sibling folders of the item (direct children of the parent), with their end lines
    sib = []
    i = pi + 1
    while i < pe:
        ln = lines[i]
        if depth_of(ln) == depth and re.search(rb'\bType="Folder"', ln):
            end = i
            if not ln.rstrip().endswith(b"/>"):
                end = i + 1
                while lines[end].rstrip() != tabs + b"</Item>":
                    end += 1
            sib.append((name_of(ln), i, end))
            i = end
        i += 1
    key = a.folder.lower()
    later = [s for s in sib if s[0].lower() > key]
    if later:
        pos, where = later[0][1], "before folder %r" % later[0][0]
    elif sib:
        pos, where = sib[-1][2] + 1, "after folder %r" % sib[-1][0]
    else:
        pos, where = si, "where the item stood"
    new = [tabs + b'<Item Name="' + a.folder.encode("utf-8") + b'" Type="Folder">',
           b"\t" + item, tabs + b"</Item>"]
    lines[pos:pos] = new
    print("%s%r (line %d) -> new folder %r at line %d (%s) | bom %s | line ending %r%s"
          % ("would move " if a.check else "moved ", a.item, si + 1, a.folder, pos + 1, where, bom,
             nl.decode("ascii"), " | dry run, nothing written" if a.check else ""))
    if not a.check:
        open(a.lvproj, "wb").write((BOM if bom else b"") + nl.join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
