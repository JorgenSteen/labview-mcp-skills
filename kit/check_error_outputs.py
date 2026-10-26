# ===========================================================================
# check_error_outputs.py - lists the error outputs a helper's AIXML leaves
# unwired: each one raises LabVIEW's automatic error dialog when it errors.
# ===========================================================================
"""Usage: python check_error_outputs.py <file.xml | folder> [...] [--quiet] [--check]

For every <Node>/<Call> of an AIXML file, an output whose terminal name starts with "error out" and whose net is
empty (`error out:`), or that is not named in the outputs at all, is reported as `file: uid <n> <node name>: <terminal>`.
An unwired error output makes LabVIEW's automatic error handling raise a MODAL dialog when that node returns an error,
and the dialog blocks the labview-mcp service (measured 2026-10-26). Exit 1 when any is found.
--quiet prints only the per-file counts. --check runs the self-test and writes nothing.
Read-only; standard library only.
"""
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ERROR_OUT = re.compile(r"^error out\b", re.I)


def unwired(xml_text):
    """(uid, node name, terminal) for every error output with an empty net."""
    found = []
    root = ET.fromstring(xml_text)
    for el in root.iter():
        if el.tag not in ("Node", "Call"):
            continue
        outputs = el.get("outputs")
        if outputs is None:
            continue
        for part in outputs.split(","):
            name, _, net = part.partition(":")
            if ERROR_OUT.match(name.strip()) and not net.strip():
                found.append((el.get("uid", "?"), el.get("_name", el.tag), name.strip()))
    return found


def files(args):
    for a in args:
        p = pathlib.Path(a)
        if p.is_dir():
            yield from sorted(p.glob("*.xml"))
        else:
            yield p


def self_test():
    sample = ('<VI _name="t.vi"><Node _name="Property Node" uid="10" outputs="Class Name:10.c,error out:"/>'
              '<Node _name="Invoke Node" uid="11" outputs="error out:11.e"/>'
              '<Call _name="x.vi" uid="12" outputs="error out (no error):"/></VI>')
    got = unwired(sample)
    assert got == [("10", "Property Node", "error out"), ("12", "x.vi", "error out (no error)")], got
    print("self-test ok")


def main(argv):
    if "--check" in argv:
        self_test()
        return 0
    quiet = "--quiet" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    total = 0
    for f in files(args):
        try:
            hits = unwired(f.read_text(encoding="utf-8"))
        except ET.ParseError as e:
            print(f"{f.name}: not parsed ({e})")
            continue
        total += len(hits)
        if hits:
            print(f"{f.name}: {len(hits)}")
            if not quiet:
                for uid, node, term in hits:
                    print(f"  uid {uid} {node}: {term}")
    print(f"total {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
