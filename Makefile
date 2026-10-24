BACKEND := backend
UV := uv --directory $(BACKEND)

.PHONY: setup check lint typecheck arch audit test mutation fmt

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

# Mutation testing on rules + risk (TESTING.md section 3): fails if any mutant survives.
mutation:
	rm -rf $(BACKEND)/mutants
	cd $(BACKEND) && uv run mutmut run > /dev/null
	@cd $(BACKEND) && survivors="$$(uv run mutmut results 2>/dev/null | grep -Ev ': killed$$' || true)"; \
	if [ -n "$$survivors" ]; then echo "Surviving mutants:"; echo "$$survivors"; exit 1; fi; \
	echo "mutation: all mutants killed"

check: lint typecheck arch test

fmt:
	$(UV) run ruff format --quiet .
	$(UV) run ruff check --fix --quiet .
