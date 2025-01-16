# Digital roadmap backend

API server providing access to Red Hat Enterprise Linux roadmap information.


## Prerequisites

Python 3.12 or later.
A container runtime such as `docker` or `podman`.


## Setup Instructions

Create a virtual environment, install the requirements, and run the server.

```shell
make install
make start-db run
```

This runs a server using the default virtual environment. Documentation can be found at  `http://127.0.0.1:8081/docs`.


## Developer Guide
Install the developer tools and run the server.

```shell
make install-dev
make start-db run
```

Alternatively you may create your own virtual environment, install the requirements, and run the server manually.
```
# After creating and activating a virtual environment
pip install -r requirements/requirements-dev-{Python version}.txt
fastapi run app/main.py --reload --host 127.0.0.1 --port 8081
```

The database runs in a container and contains data already. To specify a different container image, set `DB_IMAGE`.

```shell
export DB_IMAGE=digital-roadmap:latest
make start-db
```

To restart the database container, run `make start-db`.

To stop the database, run `make stop-db`.

### Testing

Lint and run tests.

```shell
make lint
make test
```

All `make` targets use the default virtual environment. If you want to use your own virtual environment, run the commands directly.

```shell
ruff check --fix
ruff format
pytest
pre-commit run --all-files
```


### Updating requirements

Python 3.12 and 3.13 must be available in order to generate requirements files.

The following files are used for updating requirements:

- `requirements.in` - Direct project dependencies
- `requirements-dev.in` - Requirements for development
- `requirements-test.in` - Requirements for running tests
- `constraints.txt` - Indirect project dependencies

```
make freeze
```

Commit the changes.
