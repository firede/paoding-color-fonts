# 在网页中使用

## 两种版本

**调色板版**（Paoding Sans SC、Paoding Serif SC）带两套调色板：第 0 套用于浅色背景，第 1 套用于深色背景。颜色按部件的次序分配，通常即 IDS 中的次序：⿰ 的左、⿱ 的上、⿴ 的外为第 0 个。CSS 可以选用任一套，并覆盖其中任意颜色。

**Ink 版**（Paoding Sans SC Ink、Paoding Serif SC Ink）所有部件都用文字颜色（CSS `color`），只以透明度区分：第 0 个部件 100%，第 1 个 50%，其后 75%、35%……只换字体、不写任何 CSS 时就能随深浅模式变化，但颜色不能用 CSS 改。

只有一个部件的字（丁、牛）和没有切分的字，两种版本都用文字颜色显示。

## 调色板版

```css
@font-face { font-family: "Paoding Sans SC"; src: url(PaodingSansSC-Regular.woff2) format("woff2"); }

@font-palette-values --paoding-light { font-family: "Paoding Sans SC"; base-palette: 0; }
@font-palette-values --paoding-dark { font-family: "Paoding Sans SC"; base-palette: 1; }

.text { font-family: "Paoding Sans SC", sans-serif; font-palette: --paoding-light; }
@media (prefers-color-scheme: dark) { .text { font-palette: --paoding-dark; } }
```

不设 `font-palette` 时用第 0 套。深色背景上只换字体、不写 CSS 时，用 Ink 版。

自定颜色，可带透明度：

```css
@font-palette-values --mine {
  font-family: "Paoding Sans SC";
  base-palette: 0;
  override-colors: 0 #b03a2e, 1 rgb(31 95 191 / 80%);
}
.text { font-palette: --mine; }
```

每个字先以第 0 个部件的颜色画一遍整字，再把其余部件画在上面，这样部件交界处不会露出抗锯齿造成的细缝。代价是：把第 1 个及以后的部件设成半透明时，会透出第 0 个部件的颜色。需要半透明效果时用 Ink 版。

## Ink 版

```css
@font-face { font-family: "Paoding Sans SC Ink"; src: url(PaodingSansSCInk-Regular.woff2) format("woff2"); }
.text { font-family: "Paoding Sans SC Ink", sans-serif; }
```

## 排版

竖排（`writing-mode: vertical-rl`）和标点挤压（`font-feature-settings: "palt"`，竖排为 `"vpal"`）与来源字体相同，着色部件随字形一起排列。

## 浏览器支持

- `font-palette` 和 `@font-palette-values`：Chrome 101、Firefox 107、Safari 15.4 起。
- 调色板版用 COLRv0，主流浏览器都支持。Ink 版用 COLRv1，Chrome 和 Firefox 支持；不支持的环境显示原字形。
- 规范中的 `font-palette: light | dark` 按调色板的浅色、深色标记自动选择，在 Chrome 中可用；其他浏览器未核实，上面用的是显式写法。

## 测试页

```sh
python3 -m http.server
```

打开 <http://localhost:8000/specimen/>，可切换字体、深浅模式和调色板，并试着覆盖颜色。网址参数：`?theme=light|dark&font=sans|sans-ink|serif|serif-ink&size=48&override=1`。
