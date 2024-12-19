# Digital roadmap backend

API server providing access to Red Hat Enterprise Linux roadmap information.


## Prerequisites

Python 3.9 or later.
A container runtime such as `docker` or `podman`.


## Setup Instructions

Create a virtual environment, install the requirements, and run the server.

```shell
make install
make run
```

This runs a server using the default virtual environment. Documentation can be found at  `http://127.0.0.1:8081/docs`.


## Developer Guide
Install the developer tools and run the server.

```shell
make install-dev
make run
```

Alternatively you may create your own virtual environment, install the requirements, and run the server manually.
```
# After creating and activating a virtual environment
pip install -r requirements/requirements-dev-{Python version}.txt
fastapi run app/main.py --reload --host 127.0.0.1 --port 8081
```


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

Python 3.9, 3.11, and 3.12 must be available in order to generate requirements files.

The following files are used for updating requiremetns:

- `requiremetns.in` - Direct project dependencies
- `requiremetns-dev.in` - Requirements for development
- `requiremetns-test.in` - Requirements for running tests
- `constraints.txt` - Indirect project dependencies

```
make freeze
```

Commit the changes.
