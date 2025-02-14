PROJECT_DIR=$(shell pwd)

VENV_DIR=.venvs/digital_roadmap
PYTHON ?= $(shell which python || which python3)
VENV_PYTHON=$(VENV_DIR)/bin/python
PYTHON_VERSION = $(shell $(VENV_PYTHON) -V | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
PIP=$(VENV_PYTHON) -m pip

PYTEST=$(VENV_DIR)/bin/pytest
RUFF=$(VENV_DIR)/bin/ruff
PRE_COMMIT=$(VENV_DIR)/bin/pre-commit

export PIP_DISABLE_PIP_VERSION_CHECK = 1

DB_IMAGE ?= quay.io/samdoran/digital-roadmap-data
DB_PORT ?= 5432

# Set the shell because otherwise this defaults to /bin/sh,
# which is dash on Ubuntu. The type builtin for dash does not accept flags.
SHELL = /bin/bash

# Determine container runtime, preferring Docker on macOS
OS = $(shell uname)
CONTAINER_RUNTIMES = podman docker
ifeq ($(OS), Darwin)
	CONTAINER_RUNTIMES = docker podman
endif

CONTAINER_RUNTIME ?= $(shell type -P $(CONTAINER_RUNTIMES) | head -n 1)


default: install

.PHONY: venv
venv:
	$(PYTHON) -m venv --clear $(VENV_DIR)

.PHONY: install
install: venv
	$(PIP) install --no-cache -r requirements/requirements-$(PYTHON_VERSION).txt

.PHONY: install-dev
install-dev: venv
	$(PIP) install -r requirements/requirements-dev-$(PYTHON_VERSION).txt

.PHONY: check-container-runtime
check-container-runtime:
ifeq ($(strip $(CONTAINER_RUNTIME)),)
	@echo "Missing container runtime. Could not find '$(CONTAINER_RUNTIMES)' in PATH."
	@exit 1
else
	@echo Found container runtime \'$(CONTAINER_RUNTIME)\'
endif


.PHONY: start-db
start-db: stop-db
	$(CONTAINER_RUNTIME) run --rm -d -p $(DB_PORT):5432 --name digital-roadmap-data $(DB_IMAGE)

.PHONY: stop-db
stop-db: check-container-runtime
	@$(CONTAINER_RUNTIME) stop digital-roadmap-data > /dev/null 2>&1 || true
	@sleep 0.1

.PHONY: run
run:
	$(VENV_DIR)/bin/uvicorn --app-dir src "roadmap.main:app" --reload --reload-dir src --host 127.0.0.1 --port 8081 --log-level debug

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
build: check-container-runtime
	$(CONTAINER_RUNTIME) build -t digital-roadmap:latest -f Containerfile .
