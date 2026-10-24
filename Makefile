BACKEND := backend
UV := uv --directory $(BACKEND)

.PHONY: setup check lint typecheck arch audit test fmt

setup:
	$(UV) sync --quiet

lint:
	$(UV) run ruff check --quiet .
	$(UV) run ruff format --check --quiet .

arch:
	$(UV) run lint-imports --no-cache

audit:
	$(UV) export --quiet --no-hashes --no-emit-project > /tmp/fintrade-reqs.txt
	$(UV) run pip-audit --progress-spinner off -r /tmp/fintrade-reqs.txt

typecheck:
	$(UV) run mypy --no-error-summary

test:
	$(UV) run pytest -n auto --cov --cov-report=term-missing:skip-covered

check: lint typecheck arch test

fmt:
	$(UV) run ruff format --quiet .
	$(UV) run ruff check --fix --quiet .
