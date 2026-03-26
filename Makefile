PROJECT_DIR=$(shell pwd)

VENV ?= .venvs/roadmap
PYTHON ?= $(shell command -v python || command -v python3)
PYTHON_VERSION := $(shell $(PYTHON) -V | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
VENV_PYTHON = $(VENV)/bin/python
PIP = $(VENV_PYTHON) -m pip

PYTEST = $(VENV)/bin/pytest
RUFF = $(VENV)/bin/ruff
PRE_COMMIT = $(VENV)/bin/pre-commit

export PIP_DISABLE_PIP_VERSION_CHECK = 1

ROADMAP_DB_IMAGE ?= quay.io/samdoran/roadmap-data
ROADMAP_DB_PORT ?= 5432

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
	$(PYTHON) -m venv --clear $(VENV)

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
	$(CONTAINER_RUNTIME) run --rm -d -p $(ROADMAP_DB_PORT):5432 --name roadmap-data $(ROADMAP_DB_IMAGE)

.PHONY: stop-db
stop-db: check-container-runtime
	@$(CONTAINER_RUNTIME) stop roadmap-data > /dev/null 2>&1 || true
	@sleep 0.1

.PHONY: load-host-data
load-host-data:
	@PYTHONPATH=./src/ $(VENV_PYTHON) $(PROJECT_DIR)/scripts/load_host_data.py

.PHONY: run
run:
	$(VENV)/bin/uvicorn --app-dir src "roadmap.main:app" --reload --reload-dir src --host 127.0.0.1 --port 8000 --log-level debug --log-config uvicorn_disable_logging.json

.PHONY: clean
clean:
	@rm -rf $(VENV)

.PHONY: freeze
freeze:
	@$(PYTHON) $(PROJECT_DIR)/scripts/freeze.py

.PHONY: update-konflux-refs
update-konflux-refs:
	@$(PYTHON) $(PROJECT_DIR)/scripts/update-konflux-refs.py --overwrite --file $(PROJECT_DIR)/.tekton/pipeline-build.yaml

.PHONY: lint
lint:
	@$(PRE_COMMIT) run --all-files

.PHONY: type
type:
	@$(VENV)/bin/pyright

.PHONY: sanity
sanity: lint type

.PHONY: test
test:
	@$(PYTEST)

.PHONY: build
build: check-container-runtime
	$(CONTAINER_RUNTIME) build --build-arg SOURCE_DATE_EPOCH=$(shell git log -1 --pretty=%ct main) -t roadmap:latest -f Containerfile .

KAFKA_TOPICS = platform.notifications.ingress

.PHONY: start-kafka
start-kafka: stop-kafka
	$(CONTAINER_RUNTIME) run --rm -d -p 9092:9092 --name roadmap-kafka \
		docker.io/apache/kafka:4.0.2
	@echo "Waiting for Kafka to start..."
	@until $(CONTAINER_RUNTIME) exec roadmap-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 > /dev/null 2>&1; do \
		sleep 1; \
	done
	@for topic in $(KAFKA_TOPICS); do \
		$(CONTAINER_RUNTIME) exec roadmap-kafka /opt/kafka/bin/kafka-topics.sh \
			--create --topic $$topic --partitions 3 --bootstrap-server localhost:9092 --replication-factor 1; \
	done

.PHONY: stop-kafka
stop-kafka: check-container-runtime
	@$(CONTAINER_RUNTIME) stop roadmap-kafka > /dev/null 2>&1 || true
	@sleep 0.1

.PHONY: run-notificator
run-notificator:
	ROADMAP_DEV=1 PYTHONPATH=src $(VENV_PYTHON) -m notificator

.PHONY: get-release-commit
get-release-commit:
	@$(PYTHON) $(PROJECT_DIR)/scripts/get-release-commit.py

.PHONY: bump-release
bump-release:
	@$(PYTHON) $(PROJECT_DIR)/scripts/bump-release.py

.PHONY: tag
tag:
	@$(PYTHON) $(PROJECT_DIR)/scripts/tag-release.py
