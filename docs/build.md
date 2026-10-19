# 生成

需要 [uv](https://docs.astral.sh/uv/)。

```sh
make            # 生成 dist/ 下的四个字体，.otf 和 .woff2 各一份
make check      # 用 OTS（浏览器使用的字体检查器）检查
make release    # 检查后打包到 release/<版本>/
make clean
```

`make` 先按 `sources.toml` 把固定版本的输入下载到 `data/`，核对哈希：[paoding](https://github.com/firede/paoding) 发布的思源黑体、思源宋体的部件标注，以及这两套字体本身。之后只要输入和生成代码不变，`make` 不会重复生成。字体中的时间戳取自当前提交的时间（`SOURCE_DATE_EPOCH`），同样的输入生成逐字节相同的字体。paoding 本身按 git tag 安装（`pyproject.toml`），用来从标注重建各部件。

## 用自己的切分

在 paoding 仓库里跑切分，再把运行目录传给 `make`：

```sh
make SANS_RUN=../paoding/out/sans SERIF_RUN=../paoding/out/serif
```

运行用的字体必须与 `sources.toml` 中的版本相同（按哈希核对）。同时修改 paoding 时，可以临时把 `pyproject.toml` 中 `[tool.uv.sources]` 的 paoding 改为本地路径。

## 发布

`make release` 写出发布用的文件：含 OTF、WOFF2、`OFL.txt`、`NOTICE.md` 的 zip，单独的四个 WOFF2，`SHA256SUMS`，以及发布说明 `notes.md`（各字体的字数，构建所用的提交和输入的哈希）。发布：

```sh
gh release create v0.002 release/0.002/*.zip release/0.002/*.woff2 release/0.002/SHA256SUMS \
  --title "Paoding Color Fonts 0.002" --notes-file release/0.002/notes.md
```

## 单个字体

```sh
uv run paoding-color-fonts --run data/runs/sans \
  --font data/fonts/SourceHanSansSC-Regular.otf \
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
