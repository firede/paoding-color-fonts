# The four fonts, from paoding's records of Source Han Sans and Serif SC.
#   make            fetches the pinned inputs of sources.toml into data/, then builds
#   make check      the fonts through OTS, the sanitizer browsers use
#   make release    checks them and packs them for a GitHub release under release/<version>/
# To build from runs of your own, set SANS_RUN and SERIF_RUN (see docs/build.md).

# timestamps in the fonts from the last commit, so the same inputs give the same bytes
export SOURCE_DATE_EPOCH ?= $(shell git log -1 --format=%ct)

SANS_RUN ?= data/runs/sans
SERIF_RUN ?= data/runs/serif
SANS_FONT = data/fonts/SourceHanSansSC-Regular.otf
SERIF_FONT = data/fonts/SourceHanSerifSC-Regular.otf
BUILD = uv run paoding-color-fonts
FONTS = dist/PaodingSansSC-Regular.otf dist/PaodingSansSCInk-Regular.otf \
        dist/PaodingSerifSC-Regular.otf dist/PaodingSerifSCInk-Regular.otf

.PHONY: all check release clean
all: $(FONTS)

# fetched again whenever sources.toml changes
data/.fetched: sources.toml
	rm -rf data/runs
	uv run paoding fetch --sources sources.toml --data data
	touch $@

# made by the fetch above, which the fonts depend on first
$(SANS_FONT) $(SERIF_FONT) data/runs/sans/records.jsonl data/runs/serif/records.jsonl: ;

dist/PaodingSansSC-Regular.otf: data/.fetched $(SANS_RUN)/records.jsonl $(SANS_FONT) src/paoding_color_fonts/build.py
	$(BUILD) --run $(SANS_RUN) --font $(SANS_FONT) --family "Paoding Sans SC" --out $@

dist/PaodingSansSCInk-Regular.otf: data/.fetched $(SANS_RUN)/records.jsonl $(SANS_FONT) src/paoding_color_fonts/build.py
	$(BUILD) --run $(SANS_RUN) --font $(SANS_FONT) --family "Paoding Sans SC Ink" --kind ink --out $@

dist/PaodingSerifSC-Regular.otf: data/.fetched $(SERIF_RUN)/records.jsonl $(SERIF_FONT) src/paoding_color_fonts/build.py
	$(BUILD) --run $(SERIF_RUN) --font $(SERIF_FONT) --family "Paoding Serif SC" --out $@

dist/PaodingSerifSCInk-Regular.otf: data/.fetched $(SERIF_RUN)/records.jsonl $(SERIF_FONT) src/paoding_color_fonts/build.py
	$(BUILD) --run $(SERIF_RUN) --font $(SERIF_FONT) --family "Paoding Serif SC Ink" --kind ink --out $@

check: $(FONTS)
	uv run --with opentype-sanitizer python -c 'import ots, sys; \
	bad = [f for f in sys.argv[1:] if ots.sanitize(f, "/dev/null").returncode]; \
	print("OTS:", "failed " + " ".join(bad) if bad else "ok"); sys.exit(bool(bad))' \
	$(FONTS) $(FONTS:.otf=.woff2)

release: check
	uv run python -m paoding_color_fonts.release $(FONTS) --runs $(SANS_RUN) $(SERIF_RUN)

clean:
	rm -rf dist release
