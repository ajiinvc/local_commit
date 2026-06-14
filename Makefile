# ── local-commit Makefile ──────────────────────────────────────────────────
# Provides universal commands that work for any contributor regardless of
# OS or preferred workflow.
#
# First time?   make setup
# Everyday use: local-commit          (after pip install -e .)
#                or python main.py
# ────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.ONESHELL:

# Detect Python; fall back to `python3` then `python`
PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python)
PIP    := $(shell command -v pip3 2>/dev/null || command -v pip 2>/dev/null || echo pip)

.PHONY: help setup install dev test lint typecheck clean distclean \
        docker-build docker-run build build-all

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── First-time setup ──────────────────────────────────────────────────────

setup: install download ## One-command first-time setup (install + download model)

install: ## Install package in editable mode (pip install -e .)
	$(PIP) install -e ".[dev]"

download: ## Download the LLM model (~400 MB, one-time)
	$(PYTHON) -m local_commit --setup

# ── Development ───────────────────────────────────────────────────────────

dev: install ## Install with dev extras and run setup
	$(PYTHON) -m local_commit --setup

test: ## Run all tests
	$(PYTHON) -m pytest tests/ -v

lint: ## Lint with ruff
	ruff check src/ tests/

typecheck: ## Type-check with mypy
	mypy src/

check: lint typecheck test ## Run all checks (lint + typecheck + test)

# ── Building ──────────────────────────────────────────────────────────────

build: ## Build pip wheel in dist/
	$(PYTHON) -m build

build-exe: ## Build standalone executable with PyInstaller
	$(PIP) install pyinstaller
	pyinstaller --onefile --name local-commit \
	  --add-data "src/local_commit:local_commit" \
	  --hidden-import llama_cpp \
	  --hidden-import requests \
	  run.py
	@echo "Binary at dist/local-commit$(suffix)"
	@echo "Copy it anywhere — no Python required."

# ── Docker ────────────────────────────────────────────────────────────────

docker-build: ## Build Docker image
	docker build -t local-commit .

docker-run: ## Run inside current directory (model volume: local-commit-model)
	docker run --rm \
	  -v local-commit-model:/root/.local-commit \
	  -v "$$(pwd):/repo" -w /repo \
	  local-commit $(ARGS)

docker-setup: ## Download model in Docker volume (one-time)
	docker run --rm \
	  -v local-commit-model:/root/.local-commit \
	  local-commit --setup

# ── Cleanup ───────────────────────────────────────────────────────────────

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

distclean: clean ## Remove venv and node_modules too
	rm -rf .venv venv

# ── Compatibility ─────────────────────────────────────────────────────────

# Detect OS for binary suffix
ifeq ($(OS),Windows_NT)
    suffix := .exe
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        suffix := _macos
    else
        suffix := _linux
    endif
endif
