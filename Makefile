.PHONY: help demo test lint fix build measure clean
.DEFAULT_GOAL := help

PY ?= python

help:              ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

demo:              ## Run the demo (no install, no dependencies)
	$(PY) demo.py

test:              ## Run the test suite
	$(PY) -m pytest -q

lint:              ## Check formatting and lint
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts

fix:               ## Apply formatting and autofixes
	$(PY) -m ruff format src tests scripts
	$(PY) -m ruff check --fix src tests scripts

build:             ## Build the wheel and sdist
	$(PY) -m build || uv build

measure:           ## Measure against a corpus: make measure CORPUS=path/to/data
	@test -n "$(CORPUS)" || (echo "set CORPUS=<directory of .txt, a .txt, or a .parquet>"; exit 1)
	$(PY) scripts/measure_corpus.py "$(CORPUS)" --json corpus-measurement.json

clean:             ## Remove caches and build output
	rm -rf .pytest_cache .ruff_cache dist build src/urdunlp/__pycache__ tests/__pycache__
