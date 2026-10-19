# The four fonts, from paoding runs of Source Han Sans and Serif SC.
#   make            runs paoding where a run is missing (some ten minutes a font), then builds
#   make check      the fonts through OTS, the sanitizer browsers use
#   make release    checks them and packs them for a GitHub release under release/<version>/
# PAODING, JOBS, SANS_RUN and SERIF_RUN can be set on the command line.

PAODING ?= ../paoding
JOBS ?= 8
SANS_RUN ?= $(PAODING)/out/sans
SERIF_RUN ?= $(PAODING)/out/serif
SANS_FONT = $(PAODING)/data/fonts/SourceHanSansSC-Regular.otf
SERIF_FONT = $(PAODING)/data/fonts/SourceHanSerifSC-Regular.otf
BUILD = uv run paoding-color-fonts
FONTS = dist/PaodingSansSC-Regular.otf dist/PaodingSansSCInk-Regular.otf \
        dist/PaodingSerifSC-Regular.otf dist/PaodingSerifSCInk-Regular.otf

.PHONY: all check release clean
all: $(FONTS)

$(SANS_FONT) $(SERIF_FONT):
	cd $(PAODING) && uv run paoding fetch

$(SANS_RUN)/records.jsonl: | $(SANS_FONT)
	cd $(PAODING) && uv run paoding run --font $(abspath $(SANS_FONT)) --out $(abspath $(SANS_RUN)) --jobs $(JOBS) --no-report

$(SERIF_RUN)/records.jsonl: | $(SERIF_FONT)
	cd $(PAODING) && uv run paoding run --font $(abspath $(SERIF_FONT)) --out $(abspath $(SERIF_RUN)) --jobs $(JOBS) --no-report

dist/PaodingSansSC-Regular.otf: $(SANS_RUN)/records.jsonl src/paoding_color_fonts/build.py
	$(BUILD) --run $(SANS_RUN) --font $(SANS_FONT) --family "Paoding Sans SC" --out $@

dist/PaodingSansSCInk-Regular.otf: $(SANS_RUN)/records.jsonl src/paoding_color_fonts/build.py
	$(BUILD) --run $(SANS_RUN) --font $(SANS_FONT) --family "Paoding Sans SC Ink" --kind ink --out $@

dist/PaodingSerifSC-Regular.otf: $(SERIF_RUN)/records.jsonl src/paoding_color_fonts/build.py
	$(BUILD) --run $(SERIF_RUN) --font $(SERIF_FONT) --family "Paoding Serif SC" --out $@

dist/PaodingSerifSCInk-Regular.otf: $(SERIF_RUN)/records.jsonl src/paoding_color_fonts/build.py
	$(BUILD) --run $(SERIF_RUN) --font $(SERIF_FONT) --family "Paoding Serif SC Ink" --kind ink --out $@

check: $(FONTS)
	uv run --with opentype-sanitizer python -c 'import ots, sys; \
	bad = [f for f in sys.argv[1:] if ots.sanitize(f, "/dev/null").returncode]; \
	print("OTS:", "failed " + " ".join(bad) if bad else "ok"); sys.exit(bool(bad))' \
	$(FONTS) $(FONTS:.otf=.woff2)

release: check
	uv run python -m paoding_color_fonts.release $(FONTS) --runs $(SANS_RUN) $(SERIF_RUN) --paoding $(PAODING)

clean:
	rm -rf dist release
