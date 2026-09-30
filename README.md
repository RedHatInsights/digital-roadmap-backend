[![CI](https://github.com/RedHatInsights/digital-roadmap-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/RedHatInsights/digital-roadmap-backend/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/RedHatInsights/digital-roadmap-backend/graph/badge.svg?token=1K4JGKV8EA)](https://codecov.io/gh/RedHatInsights/digital-roadmap-backend)


# Digital roadmap backend

API server providing access to Red Hat Enterprise Linux roadmap information.


## Prerequisites

- Python 3.12 or later.
- A container runtime such as `docker` or `podman`.
- To use the `/relevant/` APIs, create an [offline token] in order to generate an access token.

### Prerequisites for `psycopg` ###

In order to create a [local installation] of `psycopg`, the the following packages and configuration are required.

#### Linux ####

RHEL

```shell
PYTHON_VERSION=3.12
yum -y install "python${PYTHON_VERSION}-devel" gcc libpq-devel
```

Debian

```shell
PYTHON_VERSION=3.12
apt install -y \
    python3-pip \
    "python${PYTHON_VERSION}-dev" \
    "python${PYTHON_VERSION}-venv" \
    gcc libpq-dev
```

#### macOS ####

`libpq` is required and `pg_config` must be in the `PATH`. These directions assume `zsh`, but you can run `brew info libpq` for instructions specific to your shell.

```shell
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc
```


## Setup Instructions

Create a virtual environment, install the requirements, and run the server.

```shell
make install
make start-db load-host-data run
```

This runs a server using the default virtual environment. Documentation can be found at  `http://127.0.0.1:8000/docs`.


### Getting a token for accessing Red Hat APIs

In order to query host inventory, a Red Hat API access token is required. Access tokens are only valid for fifteen minutes and require an [offline token] in order to generate new ones.

```
export RH_OFFLINE_TOKEN_PROD="[offline token]"
export RH_TOKEN="$(./scripts/get-redhat-access-token.py)"
```

To query the Stage environment, set an appropriate token and pass in the environment parameter.
```
export RH_OFFLINE_TOKEN_STAGE="[offline token]"
export RH_TOKEN="$(./scripts/get-redhat-access-token.py -e stage)"
```

Use the access token in the request header. Here is an example using [httpie].

```
http localhost:8000/api/roadmap/v1/relevant/lifecycle/rhel/ \
 Authorization:"Bearer $RH_TOKEN"
```

## Developer Guide
Install the developer tools, load test data, and run the server. Setting `ROADMAP_DEV=1` will avoid querying RBAC and query inventory data in the local database.

```shell
export ROADMAP_DEV=1
make install-dev
make start-db load-host-data run
```

Alternatively you may create your own virtual environment, install the requirements, and run the server manually.
```
# After creating and activating a virtual environment
pip install -r requirements/requirements-dev-{Python version}.txt
uvicorn --app-dir src "roadmap.main:app" --reload --reload-dir src --host 127.0.0.1 --port 8000 --log-level debug
```

### Host Inventory ###

Running `make load-host-data` loads inventory host data from `tests/fixtures/inventory_db_response.json.gz`. It's possible to use a different file to load specific hosts into inventory for testing.

Unzip and modify the existing file or create your own. The file does not have to be gzipped but it must be valid JSON.

```
ROADMAP_HOST_DATA_FILE=path/to/file.json make load-host-data
```

#### Generating a large local inventory

The host generator needs an HBI response containing a JSON array of hosts with
system profiles. Source data can be retrieved through Gabi with `get-hosts.py`.
This requires configured Gabi access and a valid OpenShift token for the chosen
environment.

```shell
python scripts/get-hosts.py --org-id ORG_ID --environment stage --scrub
```

The response is written to `scratch/hosts-ORG_ID.json`. The `--scrub` option
removes identifying host data while preserving the system profiles used by the
roadmap service.

Existing compressed HBI data can be used instead. Uncompress it while keeping
the original archive:

```shell
gzip --decompress --keep scratch/hosts-ORG_ID.json.gz
```

Generate the required number of hosts from the source profiles. Each generated
host receives a unique UUID and display name while retaining a source system
profile. Source hosts with missing or empty system profiles are skipped.
Profiles are reused when the requested count exceeds the usable source host
count.

```shell
python scripts/generate_hosts.py \
  --input scratch/hosts-ORG_ID.json \
  --output scratch/generated-hosts-20000.json \
  --count 20000
```

Both compressed and uncompressed input files are supported. Generation is
streamed, but the output can still be large. Its size depends on the source
system profiles, particularly their installed package lists.

Start the local database and load the generated data with the streaming loader.
It inserts 100 hosts per transaction by default and does not enable SQLAlchemy
SQL logging.

```shell
make start-db
PYTHONPATH=src python scripts/load_host_data_streaming.py \
  --input scratch/generated-hosts-20000.json
```

With the application running locally, measure the relevant AppStreams and RHEL
endpoints with:

```shell
curl -sS -o /dev/null \
  -w 'AppStreams: HTTP %{http_code}, first byte %{time_starttransfer}s, total %{time_total}s\n' \
  http://127.0.0.1:8000/api/roadmap/v1/relevant/lifecycle/app-streams

curl -sS -o /dev/null \
  -w 'RHEL: HTTP %{http_code}, first byte %{time_starttransfer}s, total %{time_total}s\n' \
  http://127.0.0.1:8000/api/roadmap/v2/relevant/lifecycle/rhel
```

### Database ###

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


### Updating Konflux references

Container images used by this project are built using Konflux. Each build task uses a container image and those image references must be updated periodically.

Run `make update-konflux-refs` and commit the changes.

If a particual container image reference does not look correct, run `update-konflux-refs.py -i [image]` to list recent tags for a specific container image.


[local installation]: https://www.psycopg.org/psycopg3/docs/basic/install.html#local-installation
[offline token]: https://access.redhat.com/articles/3626371
[host inventory]: https://developers.redhat.com/api-catalog/api/inventory
[httpie]: https://httpie.io/docs/cli
