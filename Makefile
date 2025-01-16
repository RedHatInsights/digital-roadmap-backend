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
	python3 -m venv --clear $(VENV_DIR)

.PHONY: install
install: venv
	$(PIP) install -r requirements/requirements-$(PYTHON_VERSION).txt

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
build: check-container-runtime
	$(CONTAINER_RUNTIME) build -t digital-roadmap:latest -f Containerfile .
