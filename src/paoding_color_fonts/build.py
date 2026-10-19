"""Build a color structure font from a paoding run and the font it was made from.

Every character keeps its own outline as the base glyph, for renderers without
color fonts. On top of it, the parts of the flat view (they tile the glyph and
never overlap) each become a layer glyph:

- palette: COLRv0 layers colored from CPAL, with a palette for light and one
  for dark backgrounds; CSS can pick either and override any color
  (@font-palette-values).
- ink: COLRv1 layers in the text color (the foreground), parts told apart by
  alpha alone; it follows `color` with no CSS of its own.

Layers that only meet along an edge leave a hairline seam where both are
antialiased. So the whole glyph goes underneath first, in the first part's
color (palette) or the lowest alpha (ink), and the parts drawn over it are
compensated so they end at their own alpha.
"""

import argparse
import hashlib
import json
from pathlib import Path

from fontTools.colorLib.builder import ColorPaletteType, buildCOLR, buildCPAL
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

from paoding.record import realize_record
from paoding.target.outline import OutlineFont

# one color per part, by its place in the record's nodes (stacking order, bottom first)
LIGHT = ["#C8372D", "#1F5FBF", "#2E8B3E", "#B7791F", "#7B3FB0", "#13858F"]
DARK = ["#FF8A7F", "#7DB2FF", "#78D492", "#F2BE55", "#C597F2", "#5FD6DF"]
ALPHA = [1.0, 0.5, 0.75, 0.35, 0.6, 0.45]

# plain glyphs kept alongside the hanzi, when the source font has them
EXTRA = ([chr(c) for c in range(0x20, 0x7F)] + [chr(c) for c in range(0x3000, 0x3040)]
         + [chr(c) for c in range(0xFF01, 0xFF5F)] + list("—‘’“”…·"))


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


def glyph_name(char):
    cp = ord(char)
    return f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"


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
    src = TTFont(source, lazy=True)
    cmap, hmtx, glyphs = src.getBestCmap(), src["hmtx"], src.getGlyphSet()
    font = OutlineFont(source)
    wanted = set(chars) if chars else None
    records = [r for r in records if (wanted is None or r["char"] in wanted) and "units" in r]
    plain = [c for c in EXTRA if ord(c) in cmap and (wanted is None or c in wanted)]

    order, strings, metrics, mapping, color = [".notdef"], {}, {}, {}, {}
    notdef = src.getGlyphOrder()[0]
    strings[".notdef"] = charstring(glyphs[notdef].draw, hmtx[notdef][0])
    metrics[".notdef"] = hmtx[notdef]

    def add(name, draw, advance):
        order.append(name)
        strings[name] = charstring(draw, advance)
        box = bounds(draw)
        metrics[name] = (advance, box[0] if box else 0)

    for c in plain:
        g = cmap[ord(c)]
        add(glyph_name(c), glyphs[g].draw, hmtx[g][0])
        mapping[ord(c)] = glyph_name(c)
    for rec in records:
        c, g = rec["char"], cmap[ord(rec["char"])]
        base, advance = glyph_name(c), hmtx[g][0]
        add(base, glyphs[g].draw, advance)
        mapping[ord(c)] = base
        flat = realize_record(rec, font)["flat"]
        layers = []
        for k, node in enumerate(rec["nodes"]):
            path = flat.get(node)
            if path is None or not bounds(path.draw):
                continue
            name = f"{base}.p{k}"
            add(name, path.draw, advance)
            layers.append((name, k))
        if len(layers) > 1:
            color[base] = layers

    fb = FontBuilder(1000, isTTF=False)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(mapping)
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
        "uniqueFontIdentifier": f"{ps};{header['tool']}",
        "fullName": f"{family} Regular",
        "psName": ps,
        "version": "Version 0.001",
        "licenseDescription": "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
        "licenseInfoURL": "https://openfontlicense.org",
    })
    fb.setupPost()

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
    return len(records), len(color), len(order)


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
    n, colored, glyphs = build(a.run, a.font, a.out, a.family, a.kind, chars)
    print(f"{n} characters, {colored} in color, {glyphs} glyphs -> {a.out}")


if __name__ == "__main__":
    main()
