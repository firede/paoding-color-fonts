# paoding-color-fonts

按部件着色的汉字字体，由 [paoding](https://github.com/firede/paoding) 的切分生成。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/sample-dark.png">
  <img alt="庖丁解牛，依乎天理，因其固然。上：Paoding Sans SC；下：Paoding Serif SC" src="docs/images/sample-light.png">
</picture>

上：Paoding Sans SC。下：Paoding Serif SC。

| 字族 | 来源 | 着色 |
|---|---|---|
| Paoding Sans SC | 思源黑体 SC | 调色板，浅色、深色各一套 |
| Paoding Sans SC Ink | 思源黑体 SC | 文字颜色，部件以透明度区分 |
| Paoding Serif SC | 思源宋体 SC | 调色板，浅色、深色各一套 |
| Paoding Serif SC Ink | 思源宋体 SC | 文字颜色，部件以透明度区分 |

切分了 10807 字，包括《通用规范汉字表》8105 字中的 8099 个；其中有多个部件的 10709 字着色。来源字体里的其余汉字保留原字形，用文字颜色显示，不会回退到别的字体。

## 使用

```css
@font-face { font-family: "Paoding Sans SC"; src: url(PaodingSansSC-Regular.woff2) format("woff2"); }
.text { font-family: "Paoding Sans SC", sans-serif; }
```

深浅模式、自定颜色和浏览器支持，见[在网页中使用](docs/web.md)。

## 生成

```sh
make
make check
```

见[生成](docs/build.md)。

## 许可

代码采用 MIT 许可。字体衍生自思源黑体、思源宋体，采用 SIL Open Font License 1.1，见 `OFL.txt`；部件拆法的来源见 `NOTICE.md`。
