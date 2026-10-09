# =============================================================================
# make_probe.py - copies an AIXML file with its root <VI _name="..."> changed to a
# throwaway name, so a first lvai_convert_aixml_to_vi trial cannot burn the real VI name.
# Byte-exact otherwise (BOM and line endings kept). Touches no LabVIEW file.
# =============================================================================
"""
Why this exists
    A ConvertAIXMLToVI that fails leaves the VI name taken in LabVIEW's memory until the
    next restart ("burned"), so a retry under the same name fails for another reason. For an
    untried body (new construct, new helper), convert a probe copy first under a name that
    does not matter; once the probe converts and runs, convert the real file.

What it does
    Finds the root element's _name attribute (the first <VI ... _name="..."> tag), replaces
    its value, and writes the result to a new file. Nothing else in the file changes.

Usage
    python make_probe.py <src.xml> <dst.xml> [<probe name>] [--force] [--check]

    <probe name>  new _name, e.g. "_probe_ZM-CM-init.vi"; default "_probe_<old name>"
    --force       overwrite <dst.xml> if it exists (refused otherwise)
    --check       dry run: print the old and new _name and write nothing

    Convert <dst.xml> to a VI in a scratch folder (never under src/), then delete the probe.

Exit code 0 on success, 2 on a missing _name or an existing destination.
"""
import argparse
import os
import re
import sys

ROOT_NAME = re.compile(rb'<VI\b[^>]*?\s_name="([^"]*)"')


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", help="AIXML file to copy")
    p.add_argument("dst", help="probe AIXML file to write")
    p.add_argument("name", nargs="?", help='new _name (default "_probe_<old name>")')
    p.add_argument("--force", action="store_true", help="overwrite an existing destination")
    p.add_argument("--check", action="store_true", help="dry run, write nothing")
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    if os.path.abspath(a.src) == os.path.abspath(a.dst):
        sys.stderr.write("destination is the source file\n")
        return 2
    if os.path.exists(a.dst) and not a.force:
        sys.stderr.write("%s exists (use --force)\n" % a.dst)
        return 2
    data = open(a.src, "rb").read()
    m = ROOT_NAME.search(data)
    if not m:
        sys.stderr.write("no <VI ... _name=\"...\"> in %s\n" % a.src)
        return 2
    old = m.group(1).decode("utf-8")
    new = a.name or "_probe_" + old
    out = data[:m.start(1)] + new.encode("utf-8") + data[m.end(1):]
    if not a.check:
        open(a.dst, "wb").write(out)
    print("probe %s %s | _name %r -> %r" % ("would be written" if a.check else "written", a.dst, old, new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
