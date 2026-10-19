"""Pack the built fonts for a GitHub release: a zip of everything, the WOFF2 files on their own,
SHA-256 sums, and notes saying what went in."""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from fontTools.ttLib import TTFont

from .build import VERSION

REPO = "https://github.com/firede/paoding-color-fonts"
ROOT = Path(__file__).resolve().parents[2]

README = f"""Paoding Color Fonts {VERSION}

按部件着色的汉字字体，由 paoding（https://github.com/firede/paoding）的切分生成。

otf/    桌面使用
woff2/  网页使用

调色板版（Paoding Sans SC、Paoding Serif SC）带浅色、深色两套调色板，CSS 可以覆盖颜色；
Ink 版（Paoding Sans SC Ink、Paoding Serif SC Ink）用文字颜色，部件以透明度区分。
网页中的用法：{REPO}/blob/main/docs/web.md

字体衍生自思源黑体、思源宋体，采用 SIL Open Font License 1.1，见 OFL.txt；来源见 NOTICE.md。
"""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def commit(repo):
    """The checked-out commit, marked when the work tree has changes."""
    head = git(repo, "rev-parse", "--short", "HEAD")
    return head + ("（含未提交的改动）" if git(repo, "status", "--porcelain", "--untracked-files=no") else "")


def describe(path):
    font = TTFont(path, lazy=True)
    colr = font["COLR"]
    colored = len(colr.ColorLayers) if colr.version == 0 else colr.table.BaseGlyphList.BaseGlyphCount
    return {"family": font["name"].getDebugName(1), "glyphs": font["maxp"].numGlyphs,
            "characters": len(font.getBestCmap()), "colored": colored}


def run_header(run):
    with open(Path(run) / "records.jsonl", encoding="utf-8") as f:
        return json.loads(f.readline())


def notes(fonts, runs):
    rows = [describe(f) for f in fonts]
    lines = [f"Paoding Color Fonts {VERSION}。", "",
             "| 字族 | 字符 | 着色的字 | 字形 |", "|---|---|---|---|"]
    lines += [f"| {r['family']} | {r['characters']} | {r['colored']} | {r['glyphs']} |" for r in rows]
    lines += ["", f"`PaodingColorFonts-{VERSION}.zip` 含 OTF、WOFF2、`OFL.txt` 和 `NOTICE.md`；四个 WOFF2 也单独附上。"
              "GitHub 的下载地址不能直接作为网页字体引用，请放到自己的站点上。用法见"
              f"[在网页中使用]({REPO}/blob/main/docs/web.md)。", "",
              "## 构建", "",
              f"- paoding-color-fonts：{commit(ROOT)}"]
    for run in runs:
        h = run_header(run)
        refs = "、".join(f"{r['file']} `{r['sha256'][:12]}`" for r in h["reference"])
        lines.append(f"- {h['font']['file']} `{h['font']['sha256'][:12]}`：{h['tool']}，第 {h['params']['level']} 层；参照 {refs}")
    lines += ["", "## 已知限制", "",
              "- 不保留来源字体的 hinting；使用 hinting 的环境中小字号下笔画可能略细。",
              "- 不含来源字体的地区字形（`locl`）。",
              "- 只有 Regular 一种字重。"]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(prog="python -m paoding_color_fonts.release", description=__doc__.splitlines()[0])
    p.add_argument("fonts", nargs="+", help="the built .otf files; each .woff2 is beside it")
    p.add_argument("--runs", nargs="+", required=True, help="the paoding runs they were built from")
    p.add_argument("--out", default="release")
    a = p.parse_args()
    out = Path(a.out) / VERSION
    out.mkdir(parents=True, exist_ok=True)
    otfs = [Path(f) for f in a.fonts]
    woffs = [f.with_suffix(".woff2") for f in otfs]
    name = f"PaodingColorFonts-{VERSION}"
    with zipfile.ZipFile(out / f"{name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in otfs:
            z.write(f, f"{name}/otf/{f.name}")
        for f in woffs:
            z.write(f, f"{name}/woff2/{f.name}")
        for f in ("OFL.txt", "NOTICE.md"):
            z.write(ROOT / f, f"{name}/{f}")
        z.writestr(f"{name}/README.txt", README)
    for f in woffs:
        (out / f.name).write_bytes(f.read_bytes())
    assets = sorted(p for p in out.iterdir() if p.suffix in (".zip", ".woff2"))
    (out / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in assets))
    (out / "notes.md").write_text(notes(otfs, a.runs), encoding="utf-8")
    for p in assets + [out / "SHA256SUMS", out / "notes.md"]:
        print(f"{p.stat().st_size / 1e6:8.1f} MB  {p}")


if __name__ == "__main__":
    main()
