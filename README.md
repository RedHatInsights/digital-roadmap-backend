# Digital roadmap backend

FastAPI application using `uvicorn` as the ASGI server.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.9 or later

## Setup Instructions

1. Clone this repository.
2. Create a virtual environment and install the requirements.

    ```shell
    make install  # or install-dev
    ```

3. Run the server with `make run`. This will run using the default virtual environment.

    To run the server manually:
    ```
    fastapi run app/main.py --reload --host 127.0.0.1 --port 8081
    ```

4. Open docs endpoint at `http://127.0.0.1:8081/docs`

## TODO

- [ ] Contributing guide
- [ ] Tests
- [ ] CI/CD pipeline
