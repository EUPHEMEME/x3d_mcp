# Makefile v1.2 2026-08-31 — one-command build + regression tripwire for the LOA5 Anatomy Explorer (v1.2: kb gate armed KB_REQUIRE_FULL=1 at 256/256 coverage; v1.1: bundle also gzips anatomy_explorer.html)
#
# `make all` = flatten spine kb explorer census gate bundle.
# flatten is the slow stage: it is a real file rule (skeleton.x3dfrag vs
# assets/loa5/** + flatten_anatomy.py), so make skips it when nothing changed.
# Quarantined scripts (normalize_loa5_meshes.py, normalize_bone_assets.py and
# their LOA5_HAnim_Project/generators twins) are deliberately NOT referenced
# here — see their SUPERSEDED headers.

PY := $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)

BUILD    := build_anatomy
SKELETON := $(BUILD)/skeleton.x3dfrag
SPINE    := $(BUILD)/studio_spine.x3d
KB       := $(BUILD)/anatomy_kb.json
EXPLORER := anatomy_explorer.x3d

# every asset the flatten stage reads (meshes, frags, textures)
LOA5_ASSETS := $(shell find assets/loa5 -type f 2>/dev/null)

.PHONY: all flatten spine kb explorer gate census bundle serve standalone

all: flatten spine kb explorer census gate bundle

# ---- flatten: the slow stage, declared as a file rule so make can skip it ----
$(SKELETON): flatten_anatomy.py $(LOA5_ASSETS)
	$(PY) flatten_anatomy.py assets/loa5/loa5_humanoid.x3dfrag $(SKELETON)

flatten: $(SKELETON)

# ---- the rest ----------------------------------------------------------------
spine:
	$(PY) build_anatomy_spine.py

kb:
	KB_REQUIRE_FULL=1 $(PY) build_kb.py

explorer:
	$(PY) generate_anatomy_explorer.py

gate:
	$(PY) techne_gate.py $(EXPLORER) $(BUILD)/gate_receipt.png

census:
	@if $(PY) -c "import pytest" 2>/dev/null; then \
		$(PY) -m pytest tests/test_census.py -q; \
	else \
		$(PY) tests/test_census.py; \
	fi

bundle:
	gzip -kf9 $(EXPLORER)
	gzip -kf9 $(KB)
	gzip -kf9 anatomy_explorer.html

serve:
	$(PY) tools_x3d/serve_gzip.py 8099

standalone:
	$(PY) build_standalone.py $(EXPLORER) anatomy_explorer.html "LOA5 Anatomy Explorer"
