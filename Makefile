BACKEND := backend
UV := uv --directory $(BACKEND)

.PHONY: setup check lint typecheck test fmt

setup:
	$(UV) sync --quiet

lint:
	$(UV) run ruff check --quiet .
	$(UV) run ruff format --check --quiet .

typecheck:
	$(UV) run mypy --no-error-summary

test:
	$(UV) run pytest -n auto --cov --cov-report=term-missing:skip-covered

check: lint typecheck test

fmt:
	$(UV) run ruff format --quiet .
	$(UV) run ruff check --fix --quiet .
