# STRATA — Structured Type-Aware Risk Assessment Through Adaptive Calibration
# Reproducible experiments for the paper

PYTHON ?= python
SEED_COUNT ?= 20

.PHONY: install test benchmark benchmark-quick figures clean

install:
	pip install -e ".[dev]"
	pip install matplotlib

test:
	$(PYTHON) -m pytest tests/ -v

benchmark:
	SEED_COUNT=$(SEED_COUNT) $(PYTHON) scripts/run_benchmark.py

benchmark-quick:
	SEED_COUNT=1 $(PYTHON) scripts/run_benchmark.py

figures:
	$(PYTHON) scripts/plot_paper_figures.py

clean:
	rm -rf outputs/*.csv outputs/*.json outputs/*.png outputs/*.md
	rm -rf outputs/figures/
