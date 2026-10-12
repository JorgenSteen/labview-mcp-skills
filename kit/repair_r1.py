# =============================================================================
# repair_r1.py - repairs the .lvclass of an INTERFACE message written by NI's Message
# Maker ("repair R1"): inserts the Parent Libraries block (Actor Framework
# Message.lvclass) before the Class Private Data item and renames the stale member item
# "Send Template.vi" to "Send <method>.vi". Byte-exact otherwise: the BOM and the file's
# own line ending (CRLF or LF) are kept. The project must be CLOSED in LabVIEW.
# =============================================================================
"""
Why this exists
    When the Message Maker helper (lvai_create_message_class.xml) is run for an INTERFACE
    method, the class file it leaves on disk is stale (finding 00-interface-message):
      - it has no <Item Name="Parent Libraries" ...> block, so LabVIEW would load the class
        as a root class instead of a Message child;
      - its member item still says "Send Template.vi" although the VI on disk was already
        renamed to "Send <method>.vi".
    The VIs themselves are fine. This script makes the class file say what is on disk.
    Each of the two repairs is applied only where it is still missing, so a re-run is safe.

Usage
    python repair_r1.py <Msg.lvclass> <method> [--check]
           [--template "Send Template.vi"]
           [--parent-name "Actor Framework.lvlib:Message.lvclass"]
           [--parent-url "/&lt;vilib&gt;/ActorFramework/Message/Message.lvclass"]

    <method>    the method name as it appears in the Send VI's file name:
                "Send <method>.vi" (e.g. PRJ-CI-handle_package).
    --check     dry run: print what would change (with line numbers) and write nothing.

Exit code 0 when the file is repaired or already repaired, 2 on an unexpected file shape.
"""
import argparse
import sys

BOM = b"\xef\xbb\xbf"


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lvclass", help="path of the message class file (.lvclass)")
    p.add_argument("method", help="method name: the member becomes 'Send <method>.vi'")
    p.add_argument("--check", action="store_true", help="dry run, print the plan, write nothing")
    p.add_argument("--template", default="Send Template.vi",
                   help="stale member item name written by Message Maker (default: 'Send Template.vi')")
    p.add_argument("--parent-name", default="Actor Framework.lvlib:Message.lvclass",
                   help="Name attribute of the Parent item to insert")
    p.add_argument("--parent-url", default="/&lt;vilib&gt;/ActorFramework/Message/Message.lvclass",
                   help="URL attribute of the Parent item to insert (XML-escaped, as in the file)")
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    data = open(a.lvclass, "rb").read()
    bom = data.startswith(BOM)
    body = data[len(BOM):] if bom else data
    nl = b"\r\n" if b"\r\n" in body else b"\n"
    lines = body.split(nl)
    changes = []

    # 1. Parent Libraries block before the (single) Class Private Data item
    if any(b'Type="Parent Libraries"' in ln for ln in lines):
        print("parent block  : already present")
    else:
        pd = [i for i, ln in enumerate(lines) if b'Type="Class Private Data"' in ln]
        if len(pd) != 1:
            sys.exit("Class Private Data items: %d (need exactly 1)" % len(pd))
        block = [
            b'\t<Item Name="Parent Libraries" Type="Parent Libraries">',
            b'\t\t<Item Name="' + a.parent_name.encode("utf-8") + b'" Type="Parent" URL="'
            + a.parent_url.encode("utf-8") + b'"/>',
            b'\t</Item>',
        ]
        lines[pd[0]:pd[0]] = block
        changes.append("parent block  : insert 3 lines before line %d (private data item)" % (pd[0] + 1))

    # 2. rename the stale member item "<template>" -> "Send <method>.vi" (Name and URL)
    old = b'<Item Name="' + a.template.encode("utf-8") + b'" Type="VI"'
    new_name = ("Send %s.vi" % a.method).encode("utf-8")
    hits = [i for i, ln in enumerate(lines) if old in ln]
    if len(hits) > 1:
        sys.exit("member items named %r: %d (need at most 1)" % (a.template, len(hits)))
    if not hits:
        if any(b'<Item Name="' + new_name + b'" Type="VI"' in ln for ln in lines):
            print("send item     : already named %s" % new_name.decode("utf-8"))
        else:
            sys.exit("neither %r nor %r found among the member items" % (a.template, new_name.decode("utf-8")))
    else:
        i = hits[0]
        lines[i] = lines[i].replace(a.template.encode("utf-8"), new_name)
        changes.append("send item     : line %d renamed %r -> %r" % (i + 1, a.template, new_name.decode("utf-8")))

    for c in changes:
        print(("would " if a.check else "") + c)
    print("bom %s | line ending %r | %s" % (bom, nl.decode("ascii"), "nothing to do" if not changes
                                             else ("dry run, nothing written" if a.check else "written")))
    if changes and not a.check:
        open(a.lvclass, "wb").write((BOM if bom else b"") + nl.join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
