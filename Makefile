VENV=.venv
PYTHON=$(VENV)\\Scripts\\python
PIP=$(VENV)\\Scripts\\pip

venv:
	python -m venv $(VENV)

install: venv
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

install-dev: venv
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff src tests

format:
	$(PYTHON) -m black src tests

typecheck:
	$(PYTHON) -m mypy src

test:
	$(PYTHON) -m pytest -q

run:
	$(PYTHON) -m docflow.cli run config/example.config.yaml

clean:
	rm -rf build .venv .mypy_cache .pytest_cache
