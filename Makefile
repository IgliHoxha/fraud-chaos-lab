.PHONY: help venv install fmt lint test run storm openapi docker up down clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
IMAGE := fraud-chaos-lab:latest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

venv: ## Create the local virtualenv
	python3 -m venv $(VENV)

install: venv ## Install the package with dev dependencies
	$(PIP) install -e ".[dev]"

fmt: ## Auto-format and fix imports (ruff)
	$(VENV)/bin/ruff format app tests
	$(VENV)/bin/ruff check --fix app tests

lint: ## Lint (ruff)
	$(VENV)/bin/ruff check app tests
	$(VENV)/bin/ruff format --check app tests

test: ## Run the test suite
	$(VENV)/bin/pytest -q

run: ## Start the API server (dry-run unless configured)
	$(PY) -m app serve

storm: ## Fire one scenario once, e.g. make storm SCENARIO=service-1-flood
	$(PY) -m app storm $(SCENARIO)

openapi: ## Regenerate docs/openapi.yaml from the app
	$(PY) -c "import yaml; from app.main import create_app; \
		open('docs/openapi.yaml','w').write('# Generated from the FastAPI app. Regenerate with: make openapi\n' + yaml.safe_dump(create_app().openapi(), sort_keys=False))"

docker: ## Build the container image
	docker build -t $(IMAGE) .

up: ## Start the app + mock upstream via docker compose
	docker compose up --build

down: ## Stop the docker compose stack
	docker compose down

clean: ## Remove caches and the virtualenv
	rm -rf $(VENV) .pytest_cache .ruff_cache **/__pycache__ .coverage
