# Variables
VENV_DIR=venv
PYTHON=$(VENV_DIR)/bin/python
PIP=$(VENV_DIR)/bin/pip
UVICORN=$(VENV_DIR)/bin/uvicorn
RUFF=$(VENV_DIR)/bin/ruff
PROJECT_DIR=$(shell pwd)

default: install

.venv:
	python3 -m venv $(VENV_DIR)
	touch $@

.install:
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	touch $@

install: .venv .install

run: install
	$(UVICORN) app.main:app --reload --port 8081

clean:
	rm -rf $(VENV_DIR)
	rm -rf .install .venv

freeze:
	@$(PROJECT_DIR)/scripts/freeze.py

lint:
	@echo "Running lint checks..."
	@$(RUFF) check $(PROJECT_DIR) --fix
	@echo "Linting completed."

.PHONY: venv install run clean lint
