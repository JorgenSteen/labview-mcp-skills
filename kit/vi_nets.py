# ============================================================================
# vi_nets.py - prints every wire (signal) of a VI's block diagram as a list of
# its endpoints (owning node, terminal index, pane index and type, enclosing
# structures), OFFLINE: the VI is read by the pylabview bundled with
# labview-mcp, LabVIEW is not called. Read-only on the VI.
# ============================================================================
"""
Why this exists
    AIXML exports do not show everything a diagram holds (the event structure's
    dynamic terminal has no element, `05` rule 60), and a render is a picture. This
    netlist says which terminal feeds which, typed, from the saved file. Used in
    Session F to see how a production project wires its event
    registration refnum and its stop hook.

Usage
    python vi_nets.py <file.vi | bundle main .xml | *_BDHb.xml>
                      [--pylabview PATH | --scripts-dir DIR] [--work DIR]
                      [--grep TEXT] [--check]

    <file.vi>        extracted first with `pylabview -x -i <vi> -m <work>\\<name>.xml`
                     (a copy is not needed: pylabview only reads it)
    bundle .xml      a `pylv_extract` / pylabview bundle already on disk: its main .xml
                     or its *_BDHb.xml (the main .xml must sit beside it, for the types)
    --pylabview P    the pylabview.cmd to use
    --scripts-dir D  `lvai_status`'s `scriptsDirectory`; pylabview is taken from
                     <D>\\..\\pylabview\\pylabview.cmd
                     Neither given: $LVMCP_PYLABVIEW, else the newest
                     ~\\.claude\\plugins\\cache\\*\\labview-mcp\\<ver>\\bin\\pylabview\\pylabview.cmd
    --work D         extraction folder (default: a new temp folder, kept, printed)
    --grep TEXT      print only the wires whose line contains TEXT
    --check          print the pylabview found and what would be extracted; extract
                     nothing, print no wires (with a bundle: parse it, print the count)

Output: one line per wire
    WIRE <uid> <end> <-> <end> ...
    end = <class>#<uid>(<label>)[prim<id>|FP].t<terminal index> p<pane idx>:<type[:label]>
          in <structure>#<uid>/...   (innermost first)
Exit 0 ok, 2 bad input / pylabview not found / extraction failed.
Ported in the Session F audit from a scratch nets.py (which took a
hard-coded bundle); the parsing is unchanged.
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

STRUCTS = ('flatSequence', 'whileLoop', 'select', 'eventStruct', 'forLoop', 'sequenceFrame')


def find_pylabview(a):
    if a.pylabview:
        return a.pylabview
    if a.scripts_dir:
        return os.path.normpath(os.path.join(a.scripts_dir, '..', 'pylabview', 'pylabview.cmd'))
    env = os.environ.get('LVMCP_PYLABVIEW')
    if env:
        return env
    pat = os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'cache', '*', 'labview-mcp', '*',
                       'bin', 'pylabview', 'pylabview.cmd')

    def ver(p):
        v = p.split(os.sep)[-4]
        return [int(x) if x.isdigit() else 0 for x in re.split(r'[.]', v)]
    found = sorted(glob.glob(pat), key=ver)
    return found[-1] if found else None


def bdhb_of(path):
    if re.search(r'_BDHb\.xml$', path, re.I):
        return path
    d = os.path.dirname(os.path.abspath(path))
    hits = glob.glob(os.path.join(d, '*_BDHb.xml'))
    return hits[0] if hits else None


def netlist(bd_path):
    root = ET.parse(bd_path).getroot()
    parent = {c: p for p in root.iter() for c in p}

    def txt(e):
        if e is None:
            return ''
        for c in e.iter():
            if c.tag == 'text' and c.text:
                return c.text.strip().strip('"')[:40]
        return ''

    def owner_name(n):
        cl = n.get('class')
        lab = txt(n.find('label'))
        extra = ''
        if cl == 'prim':
            extra = 'prim' + (n.findtext('primResID') or '')
        if cl == 'fPTerm':
            extra = 'FP'
        return f'{cl}#{n.get("uid")}{"(" + lab + ")" if lab else ""}{"[" + extra + "]" if extra else ""}'

    mains = [f for f in glob.glob(os.path.join(os.path.dirname(bd_path), '*.xml'))
             if not re.search(r'_(BDHb|FPHb)\.xml$', f)]
    mt = open(mains[0], encoding='utf-8', errors='replace').read() if mains else ''
    h2c = {int(a): int(b) for a, b in re.findall(r'Heap TypeID\s+(\d+) = Consolidated TypeID\s+(\d+)', mt)}
    c2f = {int(a): int(b) for a, b in re.findall(r'<TypeDesc Index="(\d+)" FlatTypeID="(\d+)"', mt)}
    flat = {}
    for m in re.finditer(r'<!-- FlatTypeID (\d+): ([^>]*?) -->\s*<TypeDesc ([^>]*)>', mt):
        lab = re.search(r'Label="([^"]*)"', m.group(3))
        ty = re.search(r'Type="([^"]*)"', m.group(3))
        flat[int(m.group(1))] = (ty.group(1) if ty else '?') + (':' + lab.group(1) if lab else '')

    def tname(td):
        m = re.search(r'TypeID\((\d+)\)', td or '')
        if not m:
            return ''
        h = int(m.group(1))
        f = c2f.get(h2c.get(h, -1), -1)
        return flat.get(f, f'h{h}')

    term_owner = {}
    for n in root.iter():
        tl = n.find('termList')
        if tl is not None and n.get('class') != 'signal':
            for i, t in enumerate(tl):
                term_owner[t.get('uid')] = (n, i)
    for n in root.iter():
        if n.get('class') == 'fPTerm':
            term_owner.setdefault(n.get('uid'), (n, 0))

    def tinfo(uid):
        if uid not in term_owner:
            return f'?{uid}'
        n, i = term_owner[uid]
        t = None
        tl = n.find('termList')
        if tl is not None and i < len(tl):
            t = tl[i]
        pidx = ''
        if t is not None:
            d = t.find('dco')
            if d is not None:
                pidx = 'p' + (d.findtext('paramIdx') or '0') + ':' + tname(d.findtext('typeDesc'))
        p = parent.get(n)
        ctx = []
        while p is not None:
            if p.get('class') in STRUCTS:
                ctx.append(p.get('class') + '#' + p.get('uid'))
            p = parent.get(p)
        return f'{owner_name(n)}.t{i}{" " + pidx if pidx else ""}{" in " + "/".join(ctx) if ctx else ""}'

    lines = []
    for s in root.iter():
        if s.get('class') == 'signal':
            tl = s.find('termList')
            ends = [e.get('uid') for e in tl] if tl is not None else []
            lines.append('WIRE ' + str(s.get('uid')) + ' ' + ' <-> '.join(tinfo(u) for u in ends))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source')
    ap.add_argument('--pylabview')
    ap.add_argument('--scripts-dir')
    ap.add_argument('--work')
    ap.add_argument('--grep')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    src = os.path.abspath(a.source)
    if not os.path.isfile(src):
        sys.stderr.write(f'no such file: {src}\n')
        return 2
    if src.lower().endswith('.vi') or src.lower().endswith('.ctl'):
        pyl = find_pylabview(a)
        if not pyl or not os.path.isfile(pyl):
            sys.stderr.write(f'pylabview not found ({pyl}); pass --pylabview or --scripts-dir\n')
            return 2
        work = a.work or tempfile.mkdtemp(prefix='vi_nets_')
        name = re.sub(r'[^A-Za-z0-9_-]', '_', os.path.splitext(os.path.basename(src))[0])
        main_xml = os.path.join(work, name + '.xml')
        if a.check:
            print(f'pylabview {pyl}\nwould extract {src}\n  -> {main_xml}\ndry run, nothing extracted')
            if not a.work:
                os.rmdir(work)
            return 0
        os.makedirs(work, exist_ok=True)
        r = subprocess.run([pyl, '-x', '-i', src, '-m', main_xml], capture_output=True, text=True)
        bd = bdhb_of(main_xml)
        if r.returncode != 0 or not bd:
            sys.stderr.write(f'extraction failed (code {r.returncode}): {r.stderr[-500:]}\n')
            return 2
        sys.stderr.write(f'extracted to {work}\n')
    else:
        bd = bdhb_of(src)
        if not bd:
            sys.stderr.write(f'no *_BDHb.xml beside {src}\n')
            return 2
    lines = netlist(bd)
    if a.grep:
        lines = [x for x in lines if a.grep in x]
    if a.check:
        print(f'{len(lines)} wires in {bd}; dry run, not printed')
        return 0
    for x in lines:
        print(x)
    return 0


if __name__ == '__main__':
    sys.exit(main())
