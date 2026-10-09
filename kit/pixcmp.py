# =============================================================================
# pixcmp.py - pure-Python PNG pixel compare (no PIL needed): two PNGs, or a folder of
# icon read-back PNGs against a reference tree. Palette, gray, RGB and RGBA files compare
# by their decoded RGBA pixels, so a re-encoded icon with the same pixels counts as equal.
# =============================================================================
"""
Why this exists
    Icons are verified by reading them back from LabVIEW (icon_get_vi_icon.xml,
    icon_get_class_icon.xml, icon_get_library_icon.xml) and comparing them with the design
    PNGs. LabVIEW writes a different encoding (often 8-bit palette) than the design tool
    (RGB/RGBA), so a byte compare always fails; PIL is not installed on the build station.
    This decodes both files and compares pixels.

Decoder
    PNG colour types 0 (gray), 2 (RGB), 3 (palette), 4 (gray+alpha), 6 (RGBA); bit depth 8
    (1/2/4 for gray and palette); all five row filters; tRNS transparency. Not supported:
    16-bit and interlaced files (reported as an error).

Modes
    pair   python pixcmp.py <a.png> <b.png>
           prints both headers, the differing pixel count (RGBA and RGB-only) and the first
           few differing pixels as (x, y) a b.
    tree   python pixcmp.py --tree <readback dir> <reference dir> [--map map.json]
           for every *.png under <readback dir> (recursive) finds its reference:
             1. the same relative path under <reference dir>;
             2. else --map entry {"<readback relpath or file stem>": "<reference relpath>"};
             3. else the one PNG in the reference tree with the same file name.
           prints one line per file (OK / DIFF n px / SIZE / NO REFERENCE / AMBIGUOUS /
           ERROR) and a summary.

Options
    --ignore-alpha   compare RGB only
    --tol N          allow a per-channel difference up to N (default 0)
    --skip NAME      tree mode: file names to skip (repeatable; default preview.png)

Exit code 0 when every compared pair matches, 1 when any differs or is missing a
reference, 2 on a usage or decode error. Read-only; writes nothing.
"""
import argparse
import json
import os
import struct
import sys
import zlib

SIG = b"\x89PNG\r\n\x1a\n"


class PngError(Exception):
    pass


def decode(path):
    """Returns (width, height, colour type, bit depth), [ (r, g, b, a), ... ] row-major."""
    d = open(path, "rb").read()
    if d[:8] != SIG:
        raise PngError("not a PNG")
    pos, idat, plte, trns, hdr = 8, b"", None, None, None
    while pos + 8 <= len(d):
        ln, typ = struct.unpack(">I4s", d[pos:pos + 8])
        body = d[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body[:13])
        elif typ == b"PLTE":
            plte = [tuple(body[i:i + 3]) for i in range(0, len(body) - 2, 3)]
        elif typ == b"tRNS":
            trns = body
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if hdr is None:
        raise PngError("no IHDR")
    w, h, bd, ct, _comp, _filt, interlace = hdr
    if interlace:
        raise PngError("interlaced PNG not supported")
    chans = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ct)
    if chans is None or bd not in (1, 2, 4, 8) or (bd < 8 and ct not in (0, 3)):
        raise PngError("colour type %s / bit depth %s not supported" % (ct, bd))
    if ct == 3 and plte is None:
        raise PngError("palette image without PLTE")
    bpp = max(1, chans * bd // 8)
    stride = (w * chans * bd + 7) // 8
    raw = zlib.decompress(idat)
    prev = bytearray(stride)
    rows, off = [], 0
    for _y in range(h):
        f = raw[off]
        line = bytearray(raw[off + 1:off + 1 + stride])
        off += 1 + stride
        for i in range(stride):
            a_ = line[i - bpp] if i >= bpp else 0
            b_ = prev[i]
            c_ = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a_) & 255
            elif f == 2:
                line[i] = (line[i] + b_) & 255
            elif f == 3:
                line[i] = (line[i] + (a_ + b_) // 2) & 255
            elif f == 4:
                p = a_ + b_ - c_
                pa, pb, pc = abs(p - a_), abs(p - b_), abs(p - c_)
                line[i] = (line[i] + (a_ if pa <= pb and pa <= pc else (b_ if pb <= pc else c_))) & 255
            elif f != 0:
                raise PngError("bad filter type %d" % f)
        rows.append(bytes(line))
        prev = line

    key = None
    if trns is not None and ct == 0 and len(trns) >= 2:
        key = struct.unpack(">H", trns[:2])[0]
    elif trns is not None and ct == 2 and len(trns) >= 6:
        key = struct.unpack(">HHH", trns[:6])
    px = []
    for line in rows:
        if bd < 8:
            per = 8 // bd
            mask = (1 << bd) - 1
            vals = [(line[x // per] >> (8 - bd * (x % per + 1))) & mask for x in range(w)]
        for x in range(w):
            if ct == 3:
                idx = vals[x] if bd < 8 else line[x]
                r, g, b = plte[idx]
                al = trns[idx] if trns is not None and idx < len(trns) else 255
            elif ct == 0:
                v = vals[x] if bd < 8 else line[x]
                al = 0 if key is not None and v == key else 255
                v = v * 255 // ((1 << bd) - 1)
                r = g = b = v
            elif ct == 2:
                r, g, b = line[3 * x:3 * x + 3]
                al = 0 if key is not None and (r, g, b) == key else 255
            elif ct == 4:
                r = g = b = line[2 * x]
                al = line[2 * x + 1]
            else:
                r, g, b, al = line[4 * x:4 * x + 4]
            px.append((r, g, b, al))
    return (w, h, ct, bd), px


def diff_pixels(pa, pb, ignore_alpha, tol):
    n = 3 if ignore_alpha else 4
    return [i for i, (x, y) in enumerate(zip(pa, pb)) if any(abs(x[c] - y[c]) > tol for c in range(n))]


def compare(a, b, ignore_alpha, tol):
    """Returns (status, detail, header a, header b, diff list, pixels a, pixels b)."""
    try:
        ha, pa = decode(a)
        hb, pb = decode(b)
    except (PngError, OSError, zlib.error, struct.error, IndexError) as e:
        return "ERROR", str(e), None, None, [], [], []
    if ha[:2] != hb[:2]:
        return "SIZE", "%dx%d vs %dx%d" % (ha[0], ha[1], hb[0], hb[1]), ha, hb, [], pa, pb
    d = diff_pixels(pa, pb, ignore_alpha, tol)
    return ("DIFF" if d else "OK"), "%d px differ of %d" % (len(d), len(pa)), ha, hb, d, pa, pb


def pair_mode(args):
    st, detail, ha, hb, d, pa, pb = compare(args.a, args.b, args.ignore_alpha, args.tol)
    if ha:
        print("a: %dx%d colour type %d bit depth %d  %s" % (ha + (args.a,)))
        print("b: %dx%d colour type %d bit depth %d  %s" % (hb + (args.b,)))
    print("%s: %s" % (st, detail))
    if st == "DIFF":
        if not args.ignore_alpha:
            print("RGB only: %d px differ" % len(diff_pixels(pa, pb, True, args.tol)))
        w = ha[0]
        for i in d[:8]:
            print("  px (%d, %d)  a %s  b %s" % (i % w, i // w, pa[i], pb[i]))
    return {"OK": 0, "ERROR": 2}.get(st, 1)


def tree_mode(args):
    rb_dir, ref_dir = args.a, args.b
    skip = set(args.skip or ["preview.png"])
    mapping = json.load(open(args.map, encoding="utf-8")) if args.map else {}
    by_name = {}
    for dp, _, fs in os.walk(ref_dir):
        for f in fs:
            if f.lower().endswith(".png"):
                by_name.setdefault(f.lower(), []).append(os.path.join(dp, f))
    counts = {}
    for dp, _, fs in os.walk(rb_dir):
        for f in sorted(fs):
            if not f.lower().endswith(".png") or f in skip:
                continue
            a = os.path.join(dp, f)
            rel = os.path.relpath(a, rb_dir)
            stem = os.path.splitext(f)[0]
            ref = os.path.join(ref_dir, rel)
            if not os.path.isfile(ref):
                m = mapping.get(rel.replace("\\", "/")) or mapping.get(rel) or mapping.get(stem)
                if m:
                    ref = os.path.join(ref_dir, m if m.lower().endswith(".png") else m + ".png")
                else:
                    cands = by_name.get(f.lower(), [])
                    ref = cands[0] if len(cands) == 1 else None
                    if len(cands) > 1:
                        counts["AMBIGUOUS"] = counts.get("AMBIGUOUS", 0) + 1
                        print("AMBIGUOUS    %s: %d references named %s (use --map)" % (rel, len(cands), f))
                        continue
            if ref is None or not os.path.isfile(ref):
                counts["NO REFERENCE"] = counts.get("NO REFERENCE", 0) + 1
                print("NO REFERENCE %s" % rel)
                continue
            st, detail, *_ = compare(a, ref, args.ignore_alpha, args.tol)
            counts[st] = counts.get(st, 0) + 1
            print("%-12s %s -> %s  (%s)" % (st, rel, os.path.relpath(ref, ref_dir), detail))
    total = sum(counts.values())
    print("SUMMARY: %d file(s): %s" % (total, ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none"))
    if counts.get("ERROR"):
        return 2
    return 0 if total and counts.get("OK", 0) == total else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a", help="first PNG, or (with --tree) the read-back folder")
    p.add_argument("b", help="second PNG, or (with --tree) the reference folder")
    p.add_argument("--tree", action="store_true", help="compare a folder against a reference tree")
    p.add_argument("--map", help="tree mode: JSON {readback relpath or stem: reference relpath}")
    p.add_argument("--skip", action="append", help="tree mode: file name to skip (repeatable)")
    p.add_argument("--ignore-alpha", action="store_true", help="compare RGB only")
    p.add_argument("--tol", type=int, default=0, help="per-channel tolerance (default 0)")
    args = p.parse_args(argv)
    if args.tree:
        if not (os.path.isdir(args.a) and os.path.isdir(args.b)):
            sys.stderr.write("--tree needs two folders\n")
            return 2
        return tree_mode(args)
    return pair_mode(args)


if __name__ == "__main__":
    sys.exit(main())
