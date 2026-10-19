# 生成

需要 [uv](https://docs.astral.sh/uv/)，以及与本仓库并列的 [paoding](https://github.com/firede/paoding) 仓库（`../paoding`）。

```sh
make            # 生成 dist/ 下的四个字体，.otf 和 .woff2 各一份
make check      # 用 OTS（浏览器使用的字体检查器）检查
make clean
```

`make` 对思源黑体和思源宋体各跑一次 `paoding run`，再生成字体；缺少来源字体时先在 paoding 里执行 `paoding fetch`。paoding 的运行只在运行目录缺少记录时执行，8 个进程每套字体约一刻钟；之后只要运行记录和生成代码不变，`make` 不会重复生成。要用新的切分结果，删掉运行目录或把 `SANS_RUN`、`SERIF_RUN` 指向别的目录。

可以在命令行上设置的变量：

| 变量 | 默认 | |
|---|---|---|
| `PAODING` | `../paoding` | paoding 仓库 |
| `SANS_RUN`、`SERIF_RUN` | `$(PAODING)/out/sans`、`$(PAODING)/out/serif` | 运行目录 |
| `JOBS` | 8 | paoding run 的进程数 |

## 单个字体

```sh
uv run paoding-color-fonts --run ../paoding/out/sans \
  --font ../paoding/data/fonts/SourceHanSansSC-Regular.otf \
  --family "Paoding Sans SC" --kind palette --out dist/PaodingSansSC-Regular.otf
```

- `--run`：paoding run 的输出目录。
- `--font`：生成这次运行的那个字体文件，按哈希核对。
- `--kind`：`palette`（默认）或 `ink`。
- `--chars`：只取部分字符，字符串或 `@文件`。

## 字体的构成

- 字体由来源字体裁剪而来：保留全部汉字、ASCII、CJK 标点和全角字符，以及排版特性用到的字形，字形名与来源相同。
- 每个切分过、有多个部件的字，原轮廓作为基础字形，供不支持彩色字体的环境使用；记录的拍平视图中的每个部件是一个图层，紧跟在它的字形之后。
- 调色板版：COLRv0 + CPAL。Ink 版：COLRv1，前景色加透明度。两者都先以整字垫底，避免部件交界处的细缝。
- 竖排度量（`vhea`、`vmtx`、`VORG`）和 `BASE` 来自来源字体；图层的竖排位置与它的字形相同。
- 排版特性来自来源字体：`vert`、`vrt2`、`vpal`、`vhal`（竖排），`palt`、`halt`、`kern`（标点挤压与字距），`fwid`、`hwid`、`pwid`、`ccmp`、`liga`。不含 `locl`：它带来来源字体中日、韩、繁体等地区字形，约 18000 个，放不下。
- 约 52000 个字形，OpenType 的上限是 65535。
- 版本号在 `src/paoding_color_fonts/build.py` 的 `VERSION`。

不保留来源字体的 hinting，在使用 hinting 的环境（如 Windows、Linux）中小字号下笔画可能比来源字体略细。只有 Regular 一种字重。
