.PHONY: help install dev test lint format build serve docs deploy clean bench

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install CORTEX
	pip install -e .

dev: ## Install with dev dependencies
	pip install -e ".[dev]"

test: ## Run all tests
	@echo "🚀 Running all tests (with 60s timeout)..."
	.venv/bin/pytest tests/ -v

test-fast: ## Run fast tests (excludes slow embedding/rag tests)
	@echo "⚡ Running fast tests..."
	.venv/bin/pytest tests/ -v -m "not slow"

test-slow: ## Run only slow tests
	@echo "🐢 Running slow tests..."
	.venv/bin/pytest tests/test_graph_rag.py tests/test_mejoralo_rounds3_5.py -v
 --tb=short

lint: ## Run linter
	ruff check cortex/ tests/

format: ## Auto-format code
	ruff format cortex/ tests/

build: ## Build distribution package
	python -m build

serve: ## Start CORTEX API server (development)
	uvicorn cortex.api:app --reload --host 0.0.0.0 --port 8000

docs: ## Build documentation
	mkdocs build

docs-serve: ## Serve documentation locally
	mkdocs serve

deploy-docs: ## Deploy docs to GitHub Pages
	mkdocs gh-deploy --force

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info site/ .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

bench: ## Run benchmarks
	python benchmarks/bench_search.py

docker: ## Build Docker image
	docker build -t cortex:latest .

docker-run: ## Run CORTEX in Docker
	docker run -d --name cortex -p 8000:8000 -v cortex-data:/data cortex:latest

mcp: ## Start MCP server
	python run_mcp_server.py
