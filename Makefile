# Variables
VENV_DIR=.venvs/digital_roadmap
PYTHON=$(VENV_DIR)/bin/python
PIP=$(VENV_DIR)/bin/python -m pip
RUFF=$(VENV_DIR)/bin/ruff
PRE_COMMIT=$(VENV_DIR)/bin/pre-commit
PYTEST=$(VENV_DIR)/bin/pytest
PROJECT_DIR=$(shell pwd)
PYTHON_VERSION = $(shell python -V | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
export PIP_DISABLE_PIP_VERSION_CHECK = 1

default: install

.PHONY: venv
venv:
	python3 -m venv --clear $(VENV_DIR)

.PHONY: install
install: venv
	$(PIP) install -r requirements/requirements-$(PYTHON_VERSION).txt

.PHONY: install-dev
install-dev: venv
	$(PIP) install -r requirements/requirements-dev-$(PYTHON_VERSION).txt

.PHONY: run
run:
	$(VENV_DIR)/bin/fastapi run app/main.py --reload --host 127.0.0.1 --port 8081

.PHONY: clean
clean:
	@rm -rf $(VENV_DIR)

.PHONY: freeze
freeze:
	@$(PROJECT_DIR)/scripts/freeze.py

.PHONY: lint
lint:
	@$(PRE_COMMIT) run --all-files

.PHONY: test
test:
	@$(PYTEST)

.PHONY: build
build:
	docker build -t digital_roadmap:latest -f Containerfile .
