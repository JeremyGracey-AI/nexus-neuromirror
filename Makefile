.PHONY: help install install-dev test lint typecheck fmt check demo clean

PY ?= python3

help:
	@echo "Targets:"
	@echo "  install       Install the package"
	@echo "  install-dev   Install with dev extras (pytest, ruff, mypy)"
	@echo "  test          Run the test suite"
	@echo "  lint          Run ruff linter"
	@echo "  typecheck     Run mypy"
	@echo "  fmt           Auto-format / auto-fix with ruff"
	@echo "  check         Run lint + typecheck + test"
	@echo "  demo          Generate a synthetic EDF and run the verifier"
	@echo "  clean         Remove caches and build artifacts"

install:
	$(PY) -m pip install .

install-dev:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests

typecheck:
	$(PY) -m mypy

fmt:
	$(PY) -m ruff check --fix src tests
	$(PY) -m ruff format src tests

check: lint typecheck test

demo:
	$(PY) -m nexus_neuromirror.demo --out /tmp/nnm_demo.edf
	$(PY) -m nexus_neuromirror.cli verify /tmp/nnm_demo.edf \
		--config configs/project.example.yaml --out reports/diagnostic_demo

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
