# =============================================================================
# lvproj_add_toplevel.py - adds one-line VI items directly under "My Computer" of a
# .lvproj, just before its Dependencies item, byte-exact otherwise: the BOM and the
# file's own line ending (CRLF or LF) are kept. The project must be CLOSED in LabVIEW.
# =============================================================================
"""
Why this exists
    A top-level VI (a launcher, a test launcher) that is not a library member has to be
    listed in the project so that it opens in the project's application instance.
    lvai_add_vis_to_project needs the project open and re-saves the whole .lvproj; this
    script adds the one line, with the project closed, and changes nothing else.
    Measured in a pilot: a launcher VI and a test launcher VI next to the .lvproj.

What it does
    - finds the Dependencies line  <tabs><Item Name="Dependencies" Type="Dependencies"/>
      exactly once (the direct child of My Computer);
    - for every path given, builds  <tabs><Item Name="<file name>" Type="VI" URL="../<path>"/>
      at the same depth, with the file's own line ending, and inserts the new lines, in
      the order given, right before Dependencies;
    - REFUSES (exit 3, nothing written) when an item of that Name or that URL is already
      listed anywhere in the project, or when a path is given twice.

    The path is relative to the FOLDER of the .lvproj, with forward slashes
    (e.g. PRJ-launcher.vi, or tests/PRJ-x.vi). LabVIEW stores URLs relative to the .lvproj
    FILE, so a file next to the project is written as URL="../PRJ-launcher.vi"; the script
    adds that "../" itself.

Usage
    python lvproj_add_toplevel.py <project.lvproj> <relative vi path> [...] [--check]

    --check     dry run: print the lines that would be added and write nothing.

Exit code 0 on success, 2 when the Dependencies anchor is not found exactly once,
3 when an item is already listed (or given twice).
"""
import argparse
import re
import sys

BOM = b"\xef\xbb\xbf"
ANCHOR = re.compile(rb'^(\t*)<Item Name="Dependencies" Type="Dependencies"\s*/>\s*$')


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lvproj", help="path of the project file (.lvproj)")
    p.add_argument("paths", nargs="+", help="VI path(s) relative to the .lvproj's folder, forward slashes")
    p.add_argument("--check", action="store_true", help="dry run, print the plan, write nothing")
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    data = open(a.lvproj, "rb").read()
    bom = data.startswith(BOM)
    body = data[len(BOM):] if bom else data
    nl = b"\r\n" if b"\r\n" in body else b"\n"
    lines = body.split(nl)

    anchors = [i for i, ln in enumerate(lines) if ANCHOR.match(ln)]
    if len(anchors) != 1:
        print("Dependencies item: %d matches (need exactly 1); nothing written" % len(anchors))
        return 2
    ai = anchors[0]
    tabs = ANCHOR.match(lines[ai]).group(1)

    new, seen = [], set()
    for rel in a.paths:
        rel = rel.replace("\\", "/").lstrip("/")
        name = rel.split("/")[-1]
        url = "../" + rel
        name_b = ('Name="%s"' % name).encode("utf-8")
        url_b = ('URL="%s"' % url).encode("utf-8")
        hits = [i + 1 for i, ln in enumerate(lines)
                if ln.lstrip().startswith(b"<Item ") and (name_b in ln or url_b in ln)]
        if hits or rel in seen:
            where = ("line(s) %s" % ", ".join(map(str, hits))) if hits else "given twice"
            print("REFUSED: %s is already listed (%s); nothing written" % (name, where))
            return 3
        seen.add(rel)
        new.append(tabs + ('<Item Name="%s" Type="VI" URL="%s"/>' % (name, url)).encode("utf-8"))

    for ln in new:
        print("%s %s" % ("would add" if a.check else "add", ln.decode("utf-8").strip()))
    out = (BOM if bom else b"") + nl.join(lines[:ai] + new + lines[ai:])
    print("before line %d (Dependencies) | bom %s | line ending %r | CR %d LF %d%s"
          % (ai + 1, bom, nl.decode("ascii"), out.count(b"\r"), out.count(b"\n"),
             " | dry run, nothing written" if a.check else ""))
    if not a.check:
        open(a.lvproj, "wb").write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
