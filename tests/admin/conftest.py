import base64
import json

import pytest

from fastapi.testclient import TestClient

from roadmap.main import app


def _make_identity_header(*, is_internal: bool = True, org_id: str = "123") -> dict[str, str]:
    payload = {
        "identity": {
            "org_id": org_id,
            "type": "User",
            "user": {
                "is_internal": is_internal,
                "is_org_admin": False,
                "username": "test@redhat.com",
            },
        }
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    return {"x-rh-identity": encoded}


@pytest.fixture()
def internal_headers() -> dict[str, str]:
    return _make_identity_header(is_internal=True)


@pytest.fixture()
def external_headers() -> dict[str, str]:
    return _make_identity_header(is_internal=False)


@pytest.fixture()
def admin_client():
    """TestClient that sends the internal identity header on every request."""
    c = TestClient(app)
    c.headers.update(_make_identity_header(is_internal=True))
    return c
