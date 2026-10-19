# paoding-color-fonts

由 [paoding](../paoding) 的部件切分生成的彩色结构字体：每个汉字的各个部件用不同颜色显示。paoding 只产出结构；这个仓库是它的一种用法。

状态：早期原型。

## 字体

| 字族 | 来源 | 着色 |
|---|---|---|
| Paoding Sans SC | 思源黑体 SC Regular | 调色板（COLRv0 + CPAL） |
| Paoding Sans SC Ink | 思源黑体 SC Regular | 文字颜色加透明度（COLRv1） |
| Paoding Serif SC | 思源宋体 SC Regular | 调色板（COLRv0 + CPAL） |
| Paoding Serif SC Ink | 思源宋体 SC Regular | 文字颜色加透明度（COLRv1） |

字符集是 paoding run 覆盖的汉字，另含 ASCII、CJK 标点和全角字符（不着色）。每个字保留原字形，不支持彩色字体的环境照常以文字颜色显示。只有一个部件的字也是如此。

- **调色板版**：带两套调色板，第 0 套用于浅色背景，第 1 套用于深色背景。颜色按记录中部件的次序分配，通常即 IDS 中的次序（⿰ 的左、⿱ 的上、⿴ 的外为第 0 个）。CSS 可以选用任一套，并覆盖其中任意颜色，包括透明度。
- **Ink 版**：所有部件都用文字颜色（CSS `color`），只以透明度区分：第 0 个部件 100%，第 1 个 50%，其后 75%、35%……只换字体、不写任何 CSS 时就能随深浅模式变化。颜色不能再用 CSS 改。

## 在网页中使用

```css
@font-face { font-family: "Paoding Sans SC"; src: url(PaodingSansSC-Regular.woff2) format("woff2"); }

/* 字体自带的调色板，随深浅模式切换 */
@font-palette-values --paoding-light { font-family: "Paoding Sans SC"; base-palette: 0; }
@font-palette-values --paoding-dark { font-family: "Paoding Sans SC"; base-palette: 1; }
.text { font-family: "Paoding Sans SC", sans-serif; font-palette: --paoding-light; }
@media (prefers-color-scheme: dark) { .text { font-palette: --paoding-dark; } }

/* 或者自己定颜色（可带透明度） */
@font-palette-values --mine {
  font-family: "Paoding Sans SC";
  base-palette: 0;
  override-colors: 0 #b03a2e, 1 rgb(31 95 191 / 80%);
}
.text { font-palette: --mine; }
```

不设 `font-palette` 时用第 0 套（浅色背景）。深色背景上只换字体、不写 CSS 时，用 Ink 版更合适。

- 部件之间不重叠。为了不在部件交界处露出抗锯齿造成的细缝，每个字先以第 0 个部件的颜色画一遍整字，再把其余部件画在上面。所以在调色板版里把第 1 个及以后的部件设成半透明时，会透出第 0 个部件的颜色；需要半透明效果时，请用 Ink 版。
- `font-palette`、`@font-palette-values` 在 Chrome 101、Firefox 107、Safari 15.4 起支持。COLRv1（Ink 版）在 Chrome 和 Firefox 中可用；不支持的环境显示原字形。规范里还有 `font-palette: light | dark`，按调色板的浅色、深色标记自动选择，但各浏览器的支持情况未经核实，上面用的是显式写法。

`specimen/index.html` 是测试页：在仓库根目录运行 `python3 -m http.server`，打开 `/specimen/`，可以切换字体、深浅模式和调色板，并试着覆盖颜色。

## 生成

```sh
uv sync
uv run paoding-color-fonts --run ../paoding/out/sans-l1 \
  --font ../paoding/data/fonts/SourceHanSansSC-Regular.otf \
  --family "Paoding Sans SC" --out dist/PaodingSansSC-Regular.otf          # 调色板版
uv run paoding-color-fonts ... --family "Paoding Sans SC Ink" --kind ink --out dist/PaodingSansSCInk-Regular.otf
```

`--run` 是 paoding run 的输出目录，`--font` 必须是生成它的那个字体文件（按哈希核对）。部件取记录的拍平视图。每次生成同时写出 `.otf` 和 `.woff2`。`--chars` 只取部分字符（字符串，或 `@文件`）。

## 许可

代码采用 MIT 许可，见 `LICENSE`。生成的字体是思源黑体、思源宋体的衍生作品，采用 SIL Open Font License 1.1，见 `OFL.txt`；按其要求不使用保留名 “Source”。部件的拆法源自 MMAH 的 `dictionary.txt`（LGPL-3.0），见 `NOTICE.md`。
