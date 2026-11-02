.PHONY: install lint test coverage build validate ci clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install --editable .

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test:
	$(PYTHON) -m pytest -vv

coverage:
	$(PYTHON) -m pytest --cov=financekit --cov-branch --cov-fail-under=95 --cov-report=term-missing

build:
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

validate:
	$(PYTHON) scripts/validate_workflow.py

ci:
	$(PYTHON) scripts/run_ci_locally.py

clean:
	rm -rf build dist htmlcov test-results local-ci-output .coverage coverage.xml .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
