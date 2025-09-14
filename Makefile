.PHONY: help install install-dev test test-unit test-integration lint format type-check clean build docs api-dev api-start api-test api-health
.DEFAULT_GOAL := help

PYTHON := python3.11
PIP := pip
PYTEST := pytest
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	$(PIP) install -e .

install-dev: ## Install development dependencies
	$(PIP) install -e ".[dev]"
	$(PIP) install -r requirements-dev.txt
	pre-commit install

test: ## Run all tests
	$(PYTEST) -v

test-unit: ## Run unit tests only
	$(PYTEST) -v -m "unit or not integration"

test-integration: ## Run integration tests only
	$(PYTEST) -v -m "integration"

test-coverage: ## Run tests with coverage report
	$(PYTEST) --cov=p1diff --cov-report=html --cov-report=term-missing

lint: ## Run all linting checks
	$(FLAKE8) src/ tests/
	$(BLACK) --check src/ tests/
	$(ISORT) --check-only src/ tests/

format: ## Format code with black and isort
	$(BLACK) src/ tests/
	$(ISORT) src/ tests/

type-check: ## Run type checking with mypy
	$(MYPY) src/

check: lint type-check ## Run all checks (lint + type-check)

clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	$(PYTHON) -m build

docs: ## Generate documentation (placeholder)
	@echo "Documentation generation not implemented yet"

dev-setup: install-dev ## Complete development setup
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify installation"

# Example usage targets
example-basic: ## Run basic example
	p1diff --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
		--good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
		--cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
		--branch codex/move-prompts-to-external-template-files

example-json: ## Run example with JSON output
	p1diff --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
		--good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
		--cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
		--branch codex/move-prompts-to-external-template-files \
		--json example-output.json

# API Commands
api-dev: ## Start API server in development mode
	$(PYTHON) scripts/start_api.py --reload --log-level debug

api-start: ## Start API server in production mode
	$(PYTHON) scripts/start_api.py --host 0.0.0.0 --workers 4

api-test: ## Test API endpoints
	curl -X POST "http://localhost:8000/diff" \
		-H "Content-Type: application/json" \
		-d '{"repo_url": "https://github.com/presidioforts/direct-finetune-rag-model.git", "commit_good": "ba7765dd48c0ba51f4fd12cde48fd100aecdb743", "commit_candidate": "d7a39abec5a282b9955afdd1649a5f1bafae35f7", "branch_name": "codex/move-prompts-to-external-template-files"}'

api-health: ## Check API health
	curl -X GET "http://localhost:8000/health"
