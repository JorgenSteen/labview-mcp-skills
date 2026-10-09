# =============================================================================
# make_icons.py - generic 32x32 LabVIEW icon generator: draws every VI / class / library icon of a source tree from a per-project spec (.labview/conventions/icon-spec.json), so the icons stay consistent and reviewable from one preview sheet.
# =============================================================================
"""Usage: python make_icons.py [--spec <icon-spec.json>] [--src <folder>] [--out <folder>]
                       [--include-planned] [--check]

Why this exists
    Icons drawn by hand drift. This draws them from tables: a banner with the owner's
    abbreviation and colour, a small library glyph, and a per-VI glyph chosen by name
    pattern. The engine (font, drawing, PNG writer, preview sheet, manifest, a library of
    generic glyphs and name rules) is project-independent; everything a project decides
    (palette, classes, libraries, its own glyphs and rules, planned VIs) is in the spec.

Inputs
    --spec   the project's icon standard. Default: <repo>/.labview/conventions/icon-spec.json
             (else the older <repo>/.labview/icon-spec.json), where <repo>
             is the nearest folder at or above the current directory that holds `.labview/`
             or `.git`. Missing spec = exit 2 ("no icon standard"); start from
             icon-spec.example.json next to this script.
    --src    the LabVIEW source tree to scan for *.vi (default: spec "paths.src").
    --out    the output folder (default: spec "paths.out"). Spec paths are relative to the
             project root: the parent of the `.labview/` folder the spec sits in (at any depth),
             or the spec's own folder otherwise.
    --include-planned  also draw the spec's "planned" VIs that do not exist yet (manifest
             entries carry "planned": true).
    --check  validate the spec and report what would be drawn; writes nothing.

Output (in --out)
    <relative VI path>.png   composite icon per VI (typedefs .ctl get none)
    _own/<rel>.png           own layer (the per-VI glyph only) for VIs that get a template
    _classes/<name>.png      class template layer (banner + small library glyph + frame)
    _libs/<name>.png         library icon (a template when the library is applied to members)
    manifest.json            VI path -> {composite, class, own, planned}; "class:<n>", "lib:<n>"
    preview.png              every icon at 3x with its name, 6 per row

Glyph choice per VI (first hit wins): spec "overrides" for (owner, file); then the built-in
FIRST rules (prefix "Read ", "Write ", "Send ", name "Do") unless a spec rule has "first": true
(those run before them); then the spec "rules" in order; then the built-in rules; else the
"generic" glyph with a warning. Rules match the file name without ".vi": "contains" (default),
"prefix", "suffix" or "equals". Colours are best kept on the web-safe cube (multiples of 0x33):
LabVIEW quantises stored icons. Exit codes: 0 ok, 1 spec invalid, 2 spec missing.
"""
import json
import os
import struct
import sys
import zlib

SPEC_VERSION = 1


# ---------------------------------------------------------------- colours
def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


WHITE, BLACK = rgb("FFFFFF"), rgb("000000")
# glyph palette keys; "." is always transparent. A spec "palette" extends/overrides these.
DEFAULT_PALETTE = {
    "K": "000000", "W": "FFFFFF", "G": "009900", "g": "66CC66",
    "R": "CC0000", "r": "FF6666", "B": "0066CC", "b": "99CCFF",
    "Y": "FFCC00", "y": "FFFF99", "O": "FF6600", "N": "996633",
    "n": "CC9966", "S": "666666", "s": "CCCCCC", "P": "663399",
}

# ---------------------------------------------------------------- 3x5 font
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011",
    "D": "110101101101110", "E": "111100110100111", "F": "111100110100100",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111",
    "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010",
    "P": "110101110100100", "Q": "010101101110011", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111",
    "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111", "0": "010101101101010",
    "1": "010110010010111", "2": "110001010100111", "3": "110001010001110",
    "4": "101101111001001", "5": "111100110001110", "6": "011100110101010",
    "7": "111001010010010", "8": "010101010101010", "9": "010101011001110",
    "-": "000000111000000", " ": "000000000000000", "_": "000000000000111",
    ".": "000000000000010", ">": "100010001010100",
}

# ---------------------------------------------------------------- built-in glyphs
# library glyphs 10x10 (generic Actor Framework kinds); per-VI glyphs 16x16
BUILTIN_LIBGLYPH = {
    'plug': [
        '..SS..SS..',
        '..SS..SS..',
        'KKKKKKKKKK',
        'KbbbbbbbbK',
        'KbbbbbbbbK',
        '.KbbbbbbK.',
        '..KKKKKK..',
        '....KK....',
        '....KK....',
        '....KK....',
    ],  # interface
    'gear': [
        '..K....K..',
        '.KKK..KKK.',
        '..KKKKKK..',
        'K.KKssKK.K',
        'KKKsWWsKKK',
        'KKKsWWsKKK',
        'K.KKssKK.K',
        '..KKKKKK..',
        '.KKK..KKK.',
        '..K....K..',
    ],  # actor
    'envelope': [
        '..........',
        'KKKKKKKKKK',
        'KyyyyyyyyK',
        'KKyyyyyyKK',
        'KyKKyyKKyK',
        'KyyyKKyyyK',
        'KyyyyyyyyK',
        'KyyyyyyyyK',
        'KKKKKKKKKK',
        '..........',
    ],  # message class
}
BUILTIN_GLYPHS = {
    'read': [
        '................',
        '..KKKKKKK.......',
        '..KbbbbbK.......',
        '..KbbbbbK.......',
        '..KbbbbbK...K...',
        '..KbbbbbK...KK..',
        '..KbbbbbKKKKKGK.',
        '..KbbbbbKGGGGGGK',
        '..KbbbbbKKKKKGK.',
        '..KbbbbbK...KK..',
        '..KbbbbbK...K...',
        '..KbbbbbK.......',
        '..KbbbbbK.......',
        '..KKKKKKK.......',
        '................',
        '................',
    ],
    'write': [
        '............KK..',
        '...........KrrK.',
        '..........KrrrK.',
        '.........KYYKK..',
        '........KYYYK...',
        '.......KYYYK....',
        '......KYYYK.....',
        '.....KYYYK......',
        '....KYYYK.......',
        '...KYYYK........',
        '..KnYYK.........',
        '..KnnK..........',
        '..KKK...........',
        '................',
        '..BBBBBBBBBBB...',
        '................',
    ],
    'init': [
        '................',
        '.......GG.......',
        '.......GG.......',
        '...GG..GG..GG...',
        '..GG...GG...GG..',
        '.GG....GG....GG.',
        '.GG....GG....GG.',
        '.GG..........GG.',
        '.GG..........GG.',
        '.GG..........GG.',
        '..GG........GG..',
        '...GG......GG...',
        '....GGGGGGGG....',
        '......GGGG......',
        '................',
        '................',
    ],
    'close': [
        '................',
        '.RR..........RR.',
        '.RRR........RRR.',
        '..RRR......RRR..',
        '...RRR....RRR...',
        '....RRR..RRR....',
        '.....RRRRRR.....',
        '......RRRR......',
        '......RRRR......',
        '.....RRRRRR.....',
        '....RRR..RRR....',
        '...RRR....RRR...',
        '..RRR......RRR..',
        '.RRR........RRR.',
        '.RR..........RR.',
        '................',
    ],
    'do': [
        '......SSSS......',
        '......SSSS......',
        '..SS.SSSSSS.SS..',
        '..SSSSSSSSSSSS..',
        '...SSSSSSSSSS...',
        '..SSSSS..SSSSS..',
        'SSSSSS....SSSSSS',
        'SSSSS......SSSSS',
        'SSSSS......SSSSS',
        'SSSSSS....SSSSSS',
        '..SSSSS..SSSSS..',
        '...SSSSSSSSSS...',
        '..SSSSSSSSSSSS..',
        '..SS.SSSSSS.SS..',
        '......SSSS......',
        '......SSSS......',
    ],
    'publish': [
        '................',
        '..............B.',
        '............BBB.',
        '..........BBbB..',
        '........BBbbbB..',
        '......BBbbbbB...',
        '....BBbbbbbbB...',
        '..BBbbbbbbbB....',
        'BBBBBBBBbbbB....',
        '........BbB.....',
        '........BbB.....',
        '........BB......',
        '........B.......',
        '................',
        '................',
        '................',
    ],
    'create': [
        '................',
        '......GGGG......',
        '......GggG......',
        '......GggG......',
        '......GggG......',
        '......GggG......',
        '.GGGGGGggGGGGGG.',
        '.GggggggggggggG.',
        '.GggggggggggggG.',
        '.GGGGGGggGGGGGG.',
        '......GggG......',
        '......GggG......',
        '......GggG......',
        '......GggG......',
        '......GGGG......',
        '................',
    ],
    'json': [
        '................',
        '...BB......BB...',
        '..B..........B..',
        '..B..........B..',
        '..B..........B..',
        '..B..K.K.K...B..',
        '.B...........B..',
        'B....K.K.K....B.',
        '.B...........B..',
        '..B..K.K.K...B..',
        '..B..........B..',
        '..B..........B..',
        '..B..........B..',
        '...BB......BB...',
        '................',
        '................',
    ],
    'clock': [
        '................',
        '.....KKKKKK.....',
        '...KKWWWWWWKK...',
        '..KWWWWKWWWWWK..',
        '..KWWWWKWWWWWK..',
        '.KWWWWWKWWWWWWK.',
        '.KWWWWWKWWWWWWK.',
        '.KWWWWWKKKKWWWK.',
        '.KWWWWWWWWWWWWK.',
        '.KWWWWWWWWWWWWK.',
        '..KWWWWWWWWWWK..',
        '..KWWWWWWWWWWK..',
        '...KKWWWWWWKK...',
        '.....KKKKKK.....',
        '................',
        '................',
    ],
    'header': [
        '................',
        '..KKKKKKKKKKK...',
        '..KBBBBBBBBBK...',
        '..KBBBBBBBBBK...',
        '..KKKKKKKKKKK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSSWWK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSWWWK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSSSWK...',
        '..KWWWWWWWWWK...',
        '..KKKKKKKKKKK...',
        '................',
        '................',
        '................',
    ],
    'folder': [
        '................',
        '................',
        '.KKKKK..........',
        'KYYYYYK.........',
        'KYYYYYKKKKKKKK..',
        'KYYYYYYYYYYYYK..',
        'KYYYYYYYYYYYYK..',
        'KYYYYYYYYYYYYK..',
        'KYYYYYYYYYYYYK..',
        'KYYYYYYYYYYYYK..',
        'KYYYYYYYYYYYYK..',
        'KKKKKKKKKKKKKK..',
        '..........GGG...',
        '...........G....',
        '................',
        '................',
    ],
    'path': [
        '................',
        '.KKKK...........',
        'KYYYYK..........',
        'KYYYYKKKKK......',
        'KYYYYYYYYK......',
        'KYYYYYYYYK......',
        'KKKKKKKKKK......',
        '....S...........',
        '....S...........',
        '....SSSSS.KKKK..',
        '..........KWWK..',
        '..........KWWKK.',
        '..........KWWWK.',
        '..........KKKKK.',
        '................',
        '................',
    ],
    'append': [
        '................',
        '..KKKKKKKKK.....',
        '..KWWWWWWWKK....',
        '..KWSSSSSWWWK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSSSWK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSSWWK...',
        '..KWWWWWWWWWK...',
        '..KWGGGGGGGWK...',
        '..KWWWWWWWWWK...',
        '..KKKKKKKKKKK...',
        '............G...',
        '...........GGG..',
        '............G...',
        '................',
    ],
    'log': [
        '................',
        '..KKKKKKKKK.....',
        '..KWWWWWWWKK....',
        '..KWRRWWWWWWK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSSSWK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSSWWK...',
        '..KWWWWWWWWWK...',
        '..KWSSSSSSSWK...',
        '..KWWWWWWWWWK...',
        '..KKKKKKKKKKK...',
        '................',
        '................',
        '................',
        '................',
    ],
    'check': [
        '................',
        '..............G.',
        '.............GG.',
        '............GGG.',
        '...........GGG..',
        '..........GGG...',
        '.G.......GGG....',
        '.GG.....GGG.....',
        '.GGG...GGG......',
        '..GGG.GGG.......',
        '...GGGGG........',
        '....GGG.........',
        '.....G..........',
        '................',
        '................',
        '................',
    ],
    'pipe': [
        '................',
        '................',
        '................',
        '..........K.....',
        '..........KK....',
        '..........KGK...',
        'KKKKKKKKKKKGGK..',
        'KGGGGGGGGGGGGGK.',
        'KKKKKKKKKKKGGK..',
        '..........KGK...',
        '..........KK....',
        '..........K.....',
        '................',
        '................',
        '................',
        '................',
    ],
    'send': [
        '................',
        '................',
        'KKKKKKKKKK......',
        'KyyyyyyyyK......',
        'KKyyyyyyKK......',
        'KyKKyyKKyK..G...',
        'KyyyKKyyyK..GG..',
        'KyyyyyyyyKGGGGG.',
        'KyyyyyyyyK..GG..',
        'KKKKKKKKKK..G...',
        '................',
        '................',
        '................',
        '................',
        '................',
        '................',
    ],
    'msgdo': [
        '................',
        '................',
        'KKKKKKKKKK......',
        'KyyyyyyyyK.G....',
        'KKyyyyyyKK.GG...',
        'KyKKyyKKyK.GGG..',
        'KyyyKKyyyK.GGGG.',
        'KyyyyyyyyK.GGG..',
        'KyyyyyyyyK.GG...',
        'KKKKKKKKKK.G....',
        '................',
        '................',
        '................',
        '................',
        '................',
        '................',
    ],
    'inbox': [
        '................',
        '.......G........',
        '.......G........',
        '.......G........',
        '.......G........',
        '.....GGGGG......',
        '......GGG.......',
        '.......G........',
        '................',
        '.KKK........KKK.',
        '.KsK........KsK.',
        '.KsKKKKKKKKKKsK.',
        '.KssssssssssssK.',
        '.KKKKKKKKKKKKKK.',
        '................',
        '................',
    ],
    'launch': [
        '................',
        '.......KK.......',
        '......KWWK......',
        '......KWWK......',
        '.....KWWWWK.....',
        '.....KWBBWK.....',
        '.....KWBBWK.....',
        '.....KWWWWK.....',
        '....KKWWWWKK....',
        '...KRKWWWWKRK...',
        '...KRKKKKKKRK...',
        '...KKK.KK.KKK...',
        '.......OO.......',
        '......OYYO......',
        '......OYYO......',
        '.......OO.......',
    ],
    'launchtest': [
        '................',
        '....KK..........',
        '...KWWK.........',
        '...KWWK.........',
        '..KWWWWK........',
        '..KWBBWK........',
        '..KWBBWK.......G',
        '..KWWWWK......GG',
        '.KKWWWWKK....GGG',
        'KRKWWWWKRK..GGG.',
        'KRKKKKKKRK.GGG..',
        'KKK.KK.KKKGGG...',
        '....OO....GG....',
        '...OYYO...G.....',
        '...OYYO.........',
        '....OO..........',
    ],
    'error': [
        '................',
        '.......YY.......',
        '......KYYK......',
        '......KYYK......',
        '.....KYYYYK.....',
        '.....KYKKYK.....',
        '....KYYKKYYK....',
        '....KYYKKYYK....',
        '...KYYYKKYYYK...',
        '...KYYYYYYYYK...',
        '..KYYYYKKYYYYK..',
        '..KYYYYKKYYYYK..',
        '.KYYYYYYYYYYYYK.',
        '.KKKKKKKKKKKKKK.',
        '................',
        '................',
    ],
    'bell': [
        '................',
        '.......KK.......',
        '......KYYK......',
        '.....KYYYYK.....',
        '....KYYYYYYK....',
        '....KYYYYYYK....',
        '....KYYYYYYK....',
        '....KYYYYYYK....',
        '...KYYYYYYYYK...',
        '..KYYYYYYYYYYK..',
        '.KYYYYYYYYYYYYK.',
        '.KKKKKKKKKKKKKK.',
        '......KSSK......',
        '.......KK.......',
        '................',
        '................',
    ],
    'loop': [
        '................',
        '....BBBBBBB.....',
        '...BB.....BB.B..',
        '..BB.......BBB..',
        '.BB........BBBB.',
        '.B..............',
        '.B..............',
        '................',
        '................',
        '..............B.',
        '..............B.',
        '.BBBB........BB.',
        '..BBB.......BB..',
        '..B.BB.....BB...',
        '.....BBBBBBB....',
        '................',
    ],
    'stop': [
        '................',
        '................',
        '...KKKKKKKKKK...',
        '...KRRRRRRRRK...',
        '...KRRRRRRRRK...',
        '...KRRRRRRRRK...',
        '...KRRRRRRRRK...',
        '...KRRRRRRRRK...',
        '...KRRRRRRRRK...',
        '...KRRRRRRRRK...',
        '...KRRRRRRRRK...',
        '...KKKKKKKKKK...',
        '................',
        '................',
        '................',
        '................',
    ],
    'event': [
        '................',
        '........OOOO....',
        '.......OYYO.....',
        '......OYYO......',
        '.....OYYO.......',
        '....OYYYYOOO....',
        '...OYYYYYYO.....',
        '...OOOOOYYO.....',
        '.....OYYO.......',
        '....OYYO........',
        '...OYYO.........',
        '..OYYO..........',
        '..OYO...........',
        '..OO............',
        '................',
        '................',
    ],
    'ui': [
        '................',
        '.KKKKKKKKKKKKKK.',
        '.KBBBBBBBBBBBBK.',
        '.KBBBBBBBBBBRRK.',
        '.KKKKKKKKKKKKKK.',
        '.KWWWWWWWWWWWWK.',
        '.KWWWWWWWWWWWWK.',
        '.KWWSSSSSSWWWWK.',
        '.KWWWWWWWWWWWWK.',
        '.KWWSSSSSSSSWWK.',
        '.KWWWWWWWWWWWWK.',
        '.KWWWWWWWWKKKWK.',
        '.KWWWWWWWWKRKWK.',
        '.KWWWWWWWWKKKWK.',
        '.KKKKKKKKKKKKKK.',
        '................',
    ],
    'alert': [
        '................',
        '..KKKKKKKKKKKK..',
        '.KrrrrrrrrrrrrK.',
        '.KrrrrrKKrrrrrK.',
        '.KrrrrrKKrrrrrK.',
        '.KrrrrrKKrrrrrK.',
        '.KrrrrrKKrrrrrK.',
        '.KrrrrrrrrrrrrK.',
        '.KrrrrrKKrrrrrK.',
        '.KrrrrrrrrrrrrK.',
        '..KKKKKKKKKKKK..',
        '....KrrK........',
        '....KrK.........',
        '....KK..........',
        '................',
        '................',
    ],
    'core': [
        '......BBBB......',
        '......BBBB......',
        '..BB.BBBBBB.BB..',
        '..BBBBBBBBBBBB..',
        '...BBBBBBBBBB...',
        '..BBBBB..BBBBB..',
        'BBBBBB....BBBBBB',
        'BBBBB......BBBBB',
        'BBBBB......BBBBB',
        'BBBBBB....BBBBBB',
        '..BBBBB..BBBBB..',
        '...BBBBBBBBBB...',
        '..BBBBBBBBBBBB..',
        '..BB.BBBBBB.BB..',
        '......BBBB......',
        '......BBBB......',
    ],
    'generic': [
        '................',
        '................',
        '..KKKKKKKKKKK...',
        '..KssssssssSK...',
        '..KsKKKKKKKSK...',
        '..KssssssssSK...',
        '..KsKKKKKKKSK...',
        '..KssssssssSK...',
        '..KsKKKKKKKSK...',
        '..KssssssssSK...',
        '..KSSSSSSSSSK...',
        '..KKKKKKKKKKK...',
        '................',
        '................',
        '................',
        '................',
    ],
}

# Built-in name rules. FIRST: accessor and message names (before the spec's rules).
BUILTIN_FIRST = [
    {"match": "prefix", "pattern": "Read ", "glyph": "read"},
    {"match": "prefix", "pattern": "Write ", "glyph": "write"},
    {"match": "prefix", "pattern": "Send ", "glyph": "send"},
    {"match": "equals", "pattern": "Do", "glyph": "msgdo"},
]
# After the spec's rules: Actor Framework overrides, then generic "<prefix>-<verb>" suffixes.
BUILTIN_RULES = [
    {"pattern": "Pre Launch Init", "glyph": "launch"},
    {"pattern": "Handle Error", "glyph": "error"},
    {"pattern": "Stop Core", "glyph": "stop"},
    {"pattern": "-stop", "glyph": "stop"},
    {"pattern": "Actor Core", "glyph": "core"},
    {"pattern": "-create", "glyph": "create"},
    {"pattern": "-init", "glyph": "init"},
    {"pattern": "-close", "glyph": "close"},
    {"pattern": "-do", "glyph": "do"},
    {"pattern": "-publish", "glyph": "publish"},
    {"pattern": "-log", "glyph": "log"},
]


# ---------------------------------------------------------------- spec
class SpecError(Exception):
    pass


def find_repo(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, ".labview")) or os.path.exists(os.path.join(d, ".git")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return os.path.abspath(start)
        d = up


class Spec:
    """The loaded, validated project spec plus the merged glyph tables."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        with open(self.path, encoding="utf-8") as f:
            d = json.load(f)
        self.raw = d
        sd = os.path.dirname(self.path)
        self.root = sd
        d_ = sd
        while True:  # the parent of the .labview folder the spec sits in, at any depth
            if os.path.basename(d_) == ".labview":
                self.root = os.path.dirname(d_)
                break
            up = os.path.dirname(d_)
            if up == d_:
                break
            d_ = up
        errs, self.warnings = [], []
        if d.get("$schema_version") != SPEC_VERSION:
            errs.append("$schema_version must be %d" % SPEC_VERSION)
        pal = dict(DEFAULT_PALETTE)
        pal.update(d.get("palette", {}))
        self.palette = {".": None}
        for k, v in pal.items():
            if len(k) != 1 or k == ".":
                errs.append("palette key %r must be one character other than '.'" % k)
            elif not _hex_ok(v):
                errs.append("palette %r: colour %r is not 6 hex digits" % (k, v))
            else:
                self.palette[k] = rgb(v)
        self.libglyph = dict(BUILTIN_LIBGLYPH)
        self.libglyph.update(d.get("lib_glyphs", {}))
        self.glyphs = dict(BUILTIN_GLYPHS)
        self.glyphs.update(d.get("glyphs", {}))
        for name, rows in self.libglyph.items():
            _check_rows(errs, "lib_glyphs." + name, rows, 10, self.palette)
        for name, rows in self.glyphs.items():
            _check_rows(errs, "glyphs." + name, rows, 16, self.palette)
        self.classes = {}
        for name, c in d.get("classes", {}).items():
            self.classes[name] = self._owner(errs, "classes." + name, c)
        self.libs = {}
        for name, c in d.get("libs", {}).items():
            self.libs[name] = self._owner(errs, "libs." + name, c, need_glyph=True)
        self.no_template = list(d.get("no_template", []))
        self.flat_folders = list(d.get("flat_folders", []))
        self.library_owners = list(d.get("library_owners", []))
        self.top_level_owner = d.get("top_level_owner")
        for key in self.no_template + self.flat_folders + self.library_owners + \
                [k for k in [self.top_level_owner] if k]:
            if key not in self.classes:
                errs.append("%r is listed but has no entry in classes" % key)
        for name in self.library_owners:
            if name not in self.no_template:
                errs.append("library owner %r must also be in no_template" % name)
        for name, c in self.classes.items():
            if name not in self.no_template and c[2] is None:
                errs.append("classes.%s: a class with a template needs a lib_glyph" % name)
        self.overrides = {}
        for owner, files in d.get("overrides", {}).items():
            if owner not in self.classes:
                errs.append("overrides.%s: no such entry in classes" % owner)
            for f, o in files.items():
                lg, vg = o.get("lib_glyph"), o.get("glyph")
                if lg is not None and lg not in self.libglyph:
                    errs.append("overrides.%s.%s: unknown lib_glyph %r" % (owner, f, lg))
                if vg not in self.glyphs:
                    errs.append("overrides.%s.%s: unknown glyph %r" % (owner, f, vg))
                self.overrides[(owner, f)] = (lg, vg)
        rules = d.get("rules", [])
        for i, r in enumerate(rules):
            if r.get("match", "contains") not in ("contains", "prefix", "suffix", "equals"):
                errs.append("rules[%d]: match must be contains/prefix/suffix/equals" % i)
            if not r.get("pattern"):
                errs.append("rules[%d]: empty pattern" % i)
            if r.get("glyph") not in self.glyphs:
                errs.append("rules[%d]: unknown glyph %r" % (i, r.get("glyph")))
        builtin = d.get("use_builtin_rules", True)
        self.rules = ([r for r in rules if r.get("first")] + (BUILTIN_FIRST if builtin else [])
                      + [r for r in rules if not r.get("first")] + (BUILTIN_RULES if builtin else []))
        self.planned = list(d.get("planned", []))
        self.label_remove = list(d.get("preview", {}).get("label_remove", []))
        self.paths = d.get("paths", {})
        if errs:
            raise SpecError("\n".join(errs))

    def _owner(self, errs, where, c, need_glyph=False):
        banner, colour, lg = c.get("banner", ""), c.get("colour", ""), c.get("lib_glyph")
        if not banner or any(ch not in FONT for ch in banner):
            errs.append("%s: banner %r must use only %s" % (where, banner, "".join(sorted(FONT))))
        elif len(banner) * 4 - 1 > 30:
            errs.append("%s: banner %r is wider than the icon (max 7 characters)" % (where, banner))
        if not _hex_ok(colour):
            errs.append("%s: colour %r is not 6 hex digits" % (where, colour))
        elif any(int(colour[i:i + 2], 16) % 0x33 for i in (0, 2, 4)):
            self.warnings.append("%s: colour %s is not web-safe (LabVIEW may shift it)" % (where, colour))
        if lg is not None and lg not in self.libglyph:
            errs.append("%s: unknown lib_glyph %r" % (where, lg))
        if need_glyph and lg is None:
            errs.append("%s: a library needs a lib_glyph" % where)
        return (banner, colour, lg)

    def vi_glyph(self, name):
        """File name of a VI -> key of its per-VI glyph."""
        n = name[:-3]
        for r in self.rules:
            p, m = r["pattern"], r.get("match", "contains")
            if (m == "contains" and p in n) or (m == "prefix" and n.startswith(p)) or \
                    (m == "suffix" and n.endswith(p)) or (m == "equals" and n == p):
                return r["glyph"]
        print("warning: no glyph rule for " + name + ", using 'generic'", file=sys.stderr)
        return "generic"


def _hex_ok(v):
    return isinstance(v, str) and len(v) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in v)


def _check_rows(errs, where, rows, size, palette):
    if not isinstance(rows, list) or len(rows) != size or any(
            not isinstance(r, str) or len(r) != size for r in rows):
        errs.append("%s: must be %d strings of %d characters" % (where, size, size))
        return
    bad = sorted({k for r in rows for k in r if k not in palette})
    if bad:
        errs.append("%s: palette keys %s not defined" % (where, "".join(bad)))


# ---------------------------------------------------------------- drawing
def blank():
    return [[WHITE] * 32 for _ in range(32)]


def put(img, x, y, c):
    if c is not None and 0 <= x < 32 and 0 <= y < 32:
        img[y][x] = c


def text(img, s, x0, y0, colour):
    x = x0
    for ch in s:
        bits = FONT[ch]
        for r in range(5):
            for c in range(3):
                if bits[r * 3 + c] == "1":
                    put(img, x + c, y0 + r, colour)
        x += 4


def glyph(spec, img, rows, x0, y0):
    for y, row in enumerate(rows):
        for x, k in enumerate(row):
            put(img, x0 + x, y0 + y, spec.palette[k])


def icon(spec, banner, colour, libg, vig):
    img = blank()
    bc = rgb(colour)
    for y in range(0, 10):
        for x in range(32):
            img[y][x] = bc
    w = len(banner) * 4 - 1
    text(img, banner, (32 - w) // 2, 2, WHITE)
    if vig is None:                       # class / library icon: library glyph large, centred
        big = [[c for c in row for _ in (0, 1)] for row in spec.libglyph[libg] for _ in (0, 1)]
        glyph(spec, img, ["".join(r) for r in big], 6, 11)
    else:
        if libg:
            glyph(spec, img, spec.libglyph[libg], 1, 16)
        glyph(spec, img, spec.glyphs[vig], 14, 13)
    for i in range(32):                   # 1 px black frame
        img[0][i] = img[31][i] = img[i][0] = img[i][31] = BLACK
    return img


def template(spec, banner, colour, libg):
    """Class/library icon used as LabVIEW's template layer: banner, small library glyph,
    frame; white elsewhere (white is transparent when ApplyIconToVIs lays it over a VI)."""
    img = icon(spec, banner, colour, libg, None)
    small = blank()
    for y in range(0, 10):
        small[y] = list(img[y])
    if libg:
        glyph(spec, small, spec.libglyph[libg], 1, 16)
    for i in range(32):
        small[0][i] = small[31][i] = small[i][0] = small[i][31] = BLACK
    return small


def own_layer(spec, vig):
    """A VI's own layer: only its per-VI glyph, white elsewhere."""
    img = blank()
    glyph(spec, img, spec.glyphs[vig], 14, 13)
    return img


# ---------------------------------------------------------------- PNG
def png_bytes(img):
    h, w = len(img), len(img[0])
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in img)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_png(path, img):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png_bytes(img))


# ---------------------------------------------------------------- owners
def owner_of(spec, rel):
    """classes key of a VI: a flat folder (first path segment), the top-level owner (a VI
    directly in src/), a library owner (a folder segment naming one), or the folder holding
    the VI - a class folder or a message class folder."""
    parts = rel.replace("\\", "/").split("/")
    if parts[0] in spec.flat_folders:
        return parts[0]
    if len(parts) == 1:
        if not spec.top_level_owner:
            raise SpecError("VI %s is directly in src/ but the spec has no top_level_owner" % rel)
        return spec.top_level_owner
    for p in parts[:-1]:
        if p in spec.library_owners:
            return p
    return parts[-2]                      # class folder


def own_class(spec, rel, own):
    """The .lvclass (or library owner's .lvlib) whose icon is applied to this VI; None for
    owners without a template."""
    lib = own in spec.library_owners
    if own in spec.no_template and not lib:
        return None
    d = os.path.dirname(rel)
    return os.path.join(d, own + (".lvlib" if lib else ".lvclass"))


def plan(spec, src, include_planned):
    """[(rel, planned, owner, banner, colour, libg, vig)] for every VI to draw."""
    rels = []
    if os.path.isdir(src):
        for dp, _, fs in os.walk(src):
            for f in sorted(fs):
                if f.endswith(".vi"):
                    rels.append((os.path.relpath(os.path.join(dp, f), src), False))
    if include_planned:
        have = {r for r, _ in rels}
        rels += [(p, True) for p in (q.replace("/", os.sep) for q in spec.planned) if p not in have]
    out = []
    for rel, planned in rels:
        f = os.path.basename(rel)
        own = owner_of(spec, rel)
        if own not in spec.classes:
            raise SpecError("VI %s: owner %r has no entry in classes" % (rel, own))
        banner, colour, libg = spec.classes[own]
        if (own, f) in spec.overrides:
            libg, vig = spec.overrides[(own, f)]
        else:
            vig = spec.vi_glyph(f)
        out.append((rel, planned, own, banner, colour, libg, vig))
    return out


# ---------------------------------------------------------------- main
def generate(spec, src, out, include_planned=False):
    items = []                            # (label, rel png, img)
    manifest = {}
    for rel, planned, own, banner, colour, libg, vig in plan(spec, src, include_planned):
        f = os.path.basename(rel)
        png = rel[:-3] + ".png"
        items.append((f[:-3], png, icon(spec, banner, colour, libg, vig)))
        entry = {"composite": png, "class": own_class(spec, rel, own)}
        if entry["class"]:                      # layered: own glyph + class template
            part = os.path.join("_own", png)
            write_png(os.path.join(out, part), own_layer(spec, vig))
            entry["own"] = part
        if planned:
            entry["planned"] = True
        manifest[rel] = entry
    for name, (banner, colour, libg) in spec.classes.items():
        if name in spec.no_template:
            continue
        png = os.path.join("_classes", name + ".png")
        items.append((name + ".lvclass", png, template(spec, banner, colour, libg)))
        manifest["class:" + name] = png
    for name, (banner, colour, libg) in spec.libs.items():
        png = os.path.join("_libs", name + ".png")
        # a library owner's icon is applied to its member VIs, so it is a template too
        img = (template(spec, banner, colour, libg) if name in spec.library_owners
               else icon(spec, banner, colour, libg, None))
        items.append((name + ".lvlib", png, img))
        manifest["lib:" + name] = png
    for _, png, img in items:
        write_png(os.path.join(out, png), img)
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    sheet(spec, out, items)
    print(len(items), "icons ->", out)


def sheet(spec, out, items):
    """Preview: each icon at 3x, file name under it in the 3x5 font, 6 per row."""
    scale, cols, cw, ch = 3, 6, 150, 130
    rows = (len(items) + cols - 1) // cols
    W, H = cols * cw, rows * ch
    img = [[rgb("EEEEEE")] * W for _ in range(H)]

    def label(s, x0, y0):
        x = x0
        for c in s.upper()[:36]:
            bits = FONT.get(c, FONT[" "])
            for r in range(5):
                for k in range(3):
                    if bits[r * 3 + k] == "1" and x + k < W:
                        img[y0 + r][x + k] = BLACK
            x += 4
    for i, (name, _, ic) in enumerate(items):
        ox, oy = (i % cols) * cw + (cw - 32 * scale) // 2, (i // cols) * ch + 6
        for y in range(32):
            for x in range(32):
                for dy in range(scale):
                    for dx in range(scale):
                        img[oy + y * scale + dy][ox + x * scale + dx] = ic[y][x]
        s = name
        for r in spec.label_remove:
            s = s.replace(r, "")
        label(s[:36], (i % cols) * cw + 3, oy + 32 * scale + 6)
        if len(s) > 36:
            label(s[36:72], (i % cols) * cw + 3, oy + 32 * scale + 13)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "preview.png"), "wb") as f:
        f.write(png_bytes(img))


def check(spec, src, include_planned):
    items = plan(spec, src, include_planned)
    templ = sum(1 for it in items if own_class(spec, it[0], it[2]))
    ncls = sum(1 for n in spec.classes if n not in spec.no_template)
    print("spec ok:", spec.path)
    for w in spec.warnings:
        print("warning:", w)
    if not os.path.isdir(src):
        print("src not found (nothing scanned):", src)
    print("would draw: %d VI icons (%d planned), %d own layers, %d class templates, %d library icons, "
          "+ manifest.json and preview.png" % (len(items), sum(1 for it in items if it[1]), templ,
                                               ncls, len(spec.libs)))
    per = {}
    for it in items:
        per.setdefault(it[2], []).append(it[6])
    for own in sorted(per):
        gl = per[own]
        print("  %-36s %3d VIs  glyphs: %s" % (own, len(gl), ", ".join(sorted(set(gl)))))


def main(argv):
    args = {"--spec": None, "--src": None, "--out": None}
    flags = set()
    it = iter(argv)
    for a in it:
        if a in args:
            args[a] = next(it, None)
            if args[a] is None:
                sys.exit("missing value for " + a)
        elif a in ("--include-planned", "--check"):
            flags.add(a)
        else:
            sys.exit(__doc__)
    spec_path = args["--spec"]
    if not spec_path:
        repo = find_repo(os.getcwd())
        spec_path = os.path.join(repo, ".labview", "conventions", "icon-spec.json")
        if not os.path.isfile(spec_path) and os.path.isfile(os.path.join(repo, ".labview", "icon-spec.json")):
            spec_path = os.path.join(repo, ".labview", "icon-spec.json")
    if not os.path.isfile(spec_path):
        print("no icon standard: write .labview/conventions/icon-spec.json first (looked for %s); start from %s"
              % (os.path.abspath(spec_path),
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon-spec.example.json")),
              file=sys.stderr)
        return 2
    try:
        spec = Spec(spec_path)
        src = os.path.abspath(args["--src"] or os.path.join(spec.root, spec.paths.get("src", "src")))
        if "--check" in flags:
            check(spec, src, "--include-planned" in flags)
            return 0
        out = args["--out"] or (os.path.join(spec.root, spec.paths["out"]) if "out" in spec.paths else None)
        if not out:
            sys.exit("no output folder: pass --out or set paths.out in the spec")
        if not os.path.isdir(src):
            raise SpecError("src folder not found: " + src)
        for w in spec.warnings:
            print("warning:", w, file=sys.stderr)
        generate(spec, src, os.path.abspath(out), "--include-planned" in flags)
    except (SpecError, ValueError) as e:
        print("icon spec invalid (%s):\n%s" % (spec_path, e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
