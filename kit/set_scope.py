# =============================================================================
# set_scope.py - sets the access scope of named members of a .lvclass by a byte-exact
# edit of BOTH NI.ClassItem.MethodScope (UInt) and NI.LibItem.Scope (Int), because
# LabVIEW's next class save resets a MethodScope that was changed alone.
# The project must be CLOSED in LabVIEW.
# =============================================================================
"""
Why this exists
    The writing tools create class members public. Making a member private, protected or
    community by hand is a right-click per VI in the IDE; a scripted edit of only
    NI.ClassItem.MethodScope looks right on disk but is reset by LabVIEW's next class save
    (measured, Session B). LabVIEW itself stores a non-public member with both properties,
    e.g. NI's Actor.lvclass for Actor Core.vi:
        <Property Name="NI.ClassItem.MethodScope" Type="UInt">3</Property>
        ...
        <Property Name="NI.LibItem.Scope" Type="Int">3</Property>
    and a PUBLIC member with MethodScope 1 and no NI.LibItem.Scope line at all.

What it does
    For every named member item (<Item Name="<member>" Type="..."> at any folder depth,
    folders themselves excluded):
      - NI.ClassItem.MethodScope is set to the scope (inserted in alphabetical property
        order if it is missing);
      - scope 1 (public): an NI.LibItem.Scope line is removed, as LabVIEW writes it;
      - scope 2/3/4: NI.LibItem.Scope is set, or inserted in alphabetical property order
        (in practice as the item's last property).
    Everything else stays byte-identical: the BOM, the file's own line ending (CRLF or LF),
    indentation, the other members. Setting the scope a member already has changes nothing.
    A one-line member item (<Item .../>) is expanded to an open/close pair.

Scopes
    1 / public, 2 / private, 3 / protected, 4 / community

Usage
    python set_scope.py <class.lvclass> <scope> <member> [<member> ...] [--check]

    <member>    the item's Name attribute, e.g. "Read published_count.vi" (exact)
    --check     dry run: print what would change and write nothing.

    Afterwards run lvai_exec_state on every member touched (cold, project closed).

Exit code 0 on success, 2 when a member is not found or the file cannot be parsed.
"""
import argparse
import re
import sys

BOM = b"\xef\xbb\xbf"
SCOPES = {"1": 1, "public": 1, "2": 2, "private": 2, "3": 3, "protected": 3, "4": 4, "community": 4}
ITEM = re.compile(rb'^(\t*)<Item Name="([^"]*)" Type="([^"]*)"')
PROP = re.compile(rb'^\t*<Property Name="([^"]*)"')
METHOD = b"NI.ClassItem.MethodScope"
LIBITEM = b"NI.LibItem.Scope"


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lvclass", help="path of the class file (.lvclass)")
    p.add_argument("scope", help="1/public, 2/private, 3/protected, 4/community")
    p.add_argument("members", nargs="+", help="Name attribute of each member item (exact)")
    p.add_argument("--check", action="store_true", help="dry run, print the plan, write nothing")
    return p.parse_args(argv)


def prop_line(tabs, name, typ, value):
    return tabs + b'<Property Name="' + name + b'" Type="' + typ + b'">' + value + b"</Property>"


def set_prop(block, tabs, name, typ, value, notes):
    """block = the member's property lines; set, insert (alphabetically) or, value None, drop."""
    for k, ln in enumerate(block):
        m = PROP.match(ln)
        if m and m.group(1) == name:
            if value is None:
                notes.append("drop %s" % name.decode())
                del block[k]
                return
            new = prop_line(tabs, name, typ, value)
            if ln != new:
                notes.append("%s %s -> %s" % (name.decode(), re.sub(rb"<[^>]*>", b"", ln).decode().strip(),
                                              value.decode()))
                block[k] = new
            return
    if value is None:
        return
    k = 0
    while k < len(block):
        m = PROP.match(block[k])
        if m and m.group(1) > name:
            break
        k += 1
    block.insert(k, prop_line(tabs, name, typ, value))
    notes.append("add %s = %s" % (name.decode(), value.decode()))


def main(argv=None):
    a = parse_args(argv)
    scope = SCOPES.get(a.scope.lower())
    if scope is None:
        sys.exit("scope %r: use 1/public, 2/private, 3/protected or 4/community" % a.scope)
    val = str(scope).encode()

    data = open(a.lvclass, "rb").read()
    bom = data.startswith(BOM)
    body = data[len(BOM):] if bom else data
    nl = b"\r\n" if b"\r\n" in body else b"\n"
    lines = body.split(nl)

    wanted = set(a.members)
    done = {}
    i = 0
    while i < len(lines):
        m = ITEM.match(lines[i])
        if not (m and m.group(3) != b"Folder" and m.group(2).decode("utf-8") in wanted):
            i += 1
            continue
        name = m.group(2).decode("utf-8")
        tabs = m.group(1)
        if lines[i].rstrip().endswith(b"/>"):                   # one-line item: expand
            lines[i] = lines[i].rstrip()[:-2].rstrip() + b">"
            lines.insert(i + 1, tabs + b"</Item>")
        j = i + 1
        while j < len(lines) and not lines[j].startswith(tabs + b"</Item>"):
            j += 1
        if j == len(lines):
            sys.stderr.write("member %r: no closing </Item>\n" % name)
            return 2
        block = lines[i + 1:j]
        notes = []
        set_prop(block, tabs + b"\t", METHOD, b"UInt", val, notes)
        set_prop(block, tabs + b"\t", LIBITEM, b"Int", None if scope == 1 else val, notes)
        lines[i + 1:j] = block
        done[name] = notes or ["unchanged"]
        i = i + 1 + len(block) + 1

    missing = [x for x in a.members if x not in done]
    if missing:
        sys.stderr.write("members not found: %r\n" % missing)
        return 2
    out = (BOM if bom else b"") + nl.join(lines)
    for name in a.members:
        print("  %s: %s" % (name, "; ".join(done[name])))
    changed = out != data
    print("%sscope %d on %d member(s) | bom %s | line ending %r | %s%s"
          % ("would set " if a.check else "set ", scope, len(done), bom, nl.decode("ascii"),
             "file changes" if changed else "file unchanged",
             " | dry run, nothing written" if a.check else ""))
    if changed and not a.check:
        open(a.lvclass, "wb").write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
