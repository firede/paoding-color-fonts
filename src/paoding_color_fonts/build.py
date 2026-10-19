"""Build a color structure font from a paoding run and the font it was made from.

Every character keeps its own outline as the base glyph, for renderers without
color fonts. On top of it, the parts of the flat view (they tile the glyph and
never overlap) each become a layer glyph:

- palette: COLRv0 layers colored from CPAL, with a palette for light and one
  for dark backgrounds; CSS can pick either and override any color
  (@font-palette-values).
- ink: COLRv1 layers in the text color (the foreground), parts told apart by
  alpha alone; it follows `color` with no CSS of its own.

The font is the source cut down to its hanzi and some punctuation, keeping
the source's glyph names, so its layout (GSUB, GPOS) and vertical metrics carry
over; layers stand where their glyphs stand.

Layers that only meet along an edge leave a hairline seam where both are
antialiased. So the whole glyph goes underneath first, in the first part's
color (palette) or the lowest alpha (ink), and the parts drawn over it are
compensated so they end at their own alpha.
"""

import argparse
import hashlib
import json
from pathlib import Path

from fontTools import subset
from fontTools.colorLib.builder import ColorPaletteType, buildCOLR, buildCPAL
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

from paoding.record import realize_record
from paoding.target.outline import OutlineFont

VERSION = "0.002"

# one color per part, by its place in the record's nodes (stacking order, bottom first)
LIGHT = ["#C8372D", "#1F5FBF", "#2E8B3E", "#B7791F", "#7B3FB0", "#13858F"]
DARK = ["#FF8A7F", "#7DB2FF", "#78D492", "#F2BE55", "#C597F2", "#5FD6DF"]
ALPHA = [1.0, 0.5, 0.75, 0.35, 0.6, 0.45]

# plain glyphs kept alongside the hanzi, when the source font has them: besides these, every
# hanzi the run did not split, so text never falls back to another font
HANZI = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x3FFFF)]
EXTRA = ([chr(c) for c in range(0x20, 0x7F)] + [chr(c) for c in range(0x3000, 0x3040)]
         + [chr(c) for c in range(0xFF01, 0xFF5F)] + list("—‘’“”…·"))

# the source's features that matter in Chinese text, horizontal and vertical. Not locl: it
# reaches the source's other regional forms (Japanese, Korean, traditional), some 18000
# glyphs, which would not fit beside the layers
FEATURES = ["ccmp", "liga", "kern", "palt", "halt", "chws", "fwid", "hwid", "pwid",
            "vert", "vrt2", "vkrn", "vpal", "vhal", "vchw"]


def read_run(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    return header, [json.loads(line) for line in lines[1:]]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def charstring(draw, advance):
    pen = T2CharStringPen(advance, None)
    draw(pen)
    return pen.getCharString()


def bounds(draw):
    pen = BoundsPen(None)
    draw(pen)
    return pen.bounds


def build(run, source, out, family, kind, chars=None):
    header, records = read_run(Path(run) / "records.jsonl")
    if header["font"]["sha256"] != sha256(source):
        raise SystemExit(f"{run} was made from another version of {header['font']['file']}")
    wanted = set(chars) if chars else None
    records = [r for r in records if (wanted is None or r["char"] in wanted) and "units" in r]
    src = subset_source(source, wanted)
    order, hmtx, glyphs = list(src.getGlyphOrder()), src["hmtx"], src.getGlyphSet()
    font = OutlineFont(source)

    strings, metrics, bounds_of, color = {}, {}, {}, {}

    def add(name, draw, advance):
        strings[name] = charstring(draw, advance)
        bounds_of[name] = bounds(draw)
        metrics[name] = (advance, bounds_of[name][0] if bounds_of[name] else 0)

    for g in order:
        add(g, glyphs[g].draw, hmtx[g][0])
    for rec in records:
        base = rec["glyph"]
        if base in color or base not in glyphs:
            continue        # one glyph for several code points; or a character not wanted
        flat = realize_record(rec, font)["flat"]
        parts = [(k, flat[n]) for k, n in enumerate(rec["nodes"]) if n in flat and bounds(flat[n].draw)]
        if len(parts) < 2:
            continue        # one part: the plain glyph in the text color
        for k, path in parts:
            add(f"{base}.p{k}", path.draw, hmtx[base][0])
        color[base] = [(f"{base}.p{k}", k) for k, _ in parts]
    # each glyph's layers right after it: they share its outline, which compresses well only nearby
    order = [name for g in order for name in [g] + [n for n, _ in color.get(g, ())]]

    fb = FontBuilder(1000, isTTF=False)
    fb.setupGlyphOrder(order)
    cmap = src["cmap"]
    uvs = [(cp, vs, g) for t in cmap.tables if t.format == 14 for vs, seqs in t.uvsDict.items() for cp, g in seqs]
    fb.setupCharacterMap(src.getBestCmap(), uvs=uvs or None)
    ps = family.replace(" ", "") + "-Regular"
    fb.setupCFF(ps, {"FullName": f"{family} Regular", "FamilyName": family, "Weight": "Regular"}, strings, {})
    fb.setupHorizontalMetrics(metrics)
    hhea = src["hhea"]
    fb.setupHorizontalHeader(ascent=hhea.ascent, descent=hhea.descent, lineGap=hhea.lineGap)
    os2 = src["OS/2"]
    fb.setupOS2(sTypoAscender=os2.sTypoAscender, sTypoDescender=os2.sTypoDescender,
                sTypoLineGap=os2.sTypoLineGap, usWinAscent=os2.usWinAscent, usWinDescent=os2.usWinDescent,
                ulCodePageRange1=os2.ulCodePageRange1, ulCodePageRange2=os2.ulCodePageRange2,
                achVendID="NONE", fsType=0)
    fb.setupNameTable({
        "copyright": f"{src['name'].getDebugName(0)} Parts colored with paoding.",
        "familyName": family,
        "styleName": "Regular",
        "uniqueFontIdentifier": f"{ps};{VERSION};{header['tool']}",
        "fullName": f"{family} Regular",
        "psName": ps,
        "version": f"Version {VERSION}",
        "licenseDescription": "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
        "licenseInfoURL": "https://openfontlicense.org",
    })
    fb.setupPost()
    fb.font["head"].fontRevision = float(VERSION)
    _vertical(fb, src, color, bounds_of)
    # layout as the source has it: the glyphs keep their names, so the tables carry over
    for tag in ("GDEF", "GSUB", "GPOS", "BASE"):
        if tag in src:
            fb.font[tag] = src[tag]

    if kind == "palette":
        rgba = lambda hexes: [tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)) + (1.0,) for h in hexes]
        fb.font["CPAL"] = buildCPAL(
            [rgba(LIGHT), rgba(DARK)],
            paletteTypes=[ColorPaletteType.USABLE_WITH_LIGHT_BACKGROUND, ColorPaletteType.USABLE_WITH_DARK_BACKGROUND],
            paletteLabels=["Light", "Dark"], nameTable=fb.font["name"])
        # the whole glyph underneath in the first part's color, so no seam shows between parts
        fb.font["COLR"] = buildCOLR({
            base: [(base, layers[0][1] % len(LIGHT))] + [(name, k % len(LIGHT)) for name, k in layers[1:]]
            for base, layers in color.items()})
    else:
        fb.font["CPAL"] = buildCPAL([[(0.0, 0.0, 0.0, 1.0)]])
        fb.font["COLR"] = buildCOLR({base: _ink(base, layers) for base, layers in color.items()},
                                    version=1, glyphMap=fb.font.getReverseGlyphMap())
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fb.font.save(out)
    fb.font.flavor = "woff2"
    fb.font.save(out.with_suffix(".woff2"))
    return len(records), len(color), len(glyphs), len(order)


def subset_source(source, wanted=None):
    """The source font cut down to the hanzi and EXTRA (or the wanted characters among them),
    with its layout tables and the glyphs they reach, under the source's own glyph names."""
    src = TTFont(source)
    unicodes = [cp for cp in src.getBestCmap()
                if (any(a <= cp <= b for a, b in HANZI) or chr(cp) in EXTRA) and (wanted is None or chr(cp) in wanted)]
    opts = subset.Options()
    opts.layout_features = FEATURES
    opts.drop_tables = [t for t in opts.drop_tables if t != "BASE"]
    opts.notdef_outline = opts.glyph_names = True
    opts.name_IDs = ["*"]
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=unicodes)
    sub.subset(src)
    return src


def _vertical(fb, src, color, bounds_of):
    """vhea, vmtx and VORG from the source; a layer stands where its glyph stands."""
    if "vmtx" not in src:
        return
    vmtx, vorg = src["vmtx"].metrics, src["VORG"] if "VORG" in src else None
    origin = lambda g: vorg.VOriginRecords.get(g, vorg.defaultVertOriginY) if vorg else None
    metrics = dict(vmtx)
    for base, layers in color.items():
        for name, _ in layers:
            box = bounds_of[name]
            y = origin(base)
            metrics[name] = (vmtx[base][0], round(y - box[3]) if y is not None else vmtx[base][1])
            if vorg and base in vorg.VOriginRecords:
                vorg.VOriginRecords[name] = vorg.VOriginRecords[base]
    vhea = src["vhea"]
    fb.setupVerticalHeader(ascent=vhea.ascent, descent=vhea.descent, lineGap=vhea.lineGap)
    fb.setupVerticalMetrics(metrics)
    if vorg:
        vorg.numVertOriginYMetrics = len(vorg.VOriginRecords)
        fb.font["VORG"] = vorg


def _ink(base, layers):
    """The whole glyph at the lowest alpha of its parts, then each part brought up to its own:
    alpha x over m gives m + x (1 - m)."""
    alpha = {name: ALPHA[k % len(ALPHA)] for name, k in layers}
    low = min(alpha.values())
    solid = lambda a: {"Format": ot.PaintFormat.PaintSolid, "PaletteIndex": 0xFFFF, "Alpha": a}
    paints = [{"Format": ot.PaintFormat.PaintGlyph, "Paint": solid(low), "Glyph": base}]
    for name, a in alpha.items():
        if a > low:
            paints.append({"Format": ot.PaintFormat.PaintGlyph, "Paint": solid(round((a - low) / (1 - low), 4)),
                           "Glyph": name})
    return {"Format": ot.PaintFormat.PaintColrLayers, "Layers": paints}


def main():
    p = argparse.ArgumentParser(prog="paoding-color-fonts", description=__doc__.splitlines()[0])
    p.add_argument("--run", required=True, help="a paoding run directory (records.jsonl)")
    p.add_argument("--font", required=True, help="the font the run was made from")
    p.add_argument("--family", required=True, help='family name, e.g. "Paoding Sans SC"')
    p.add_argument("--kind", choices=["palette", "ink"], default="palette")
    p.add_argument("--chars", help="only these characters (a string, or @file)")
    p.add_argument("--out", required=True, help="output .otf (a .woff2 is written beside it)")
    a = p.parse_args()
    chars = a.chars
    if chars and chars.startswith("@"):
        chars = Path(chars[1:]).read_text(encoding="utf-8")
    n, colored, source, glyphs = build(a.run, a.font, a.out, a.family, a.kind, chars)
    print(f"{n} characters split, {colored} of them in color; "
          f"{source} glyphs from the source and {glyphs - source} layers -> {a.out}")


if __name__ == "__main__":
    main()
