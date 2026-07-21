import pytest

from notificator.notificator import Notificator
from roadmap.config import Settings

from .utils import FIXED_DATETIME
from .utils import ORG_ID


@pytest.fixture(autouse=True)
def clear_settings_cache():
    Settings.create.cache_clear()
    yield
    Settings.create.cache_clear()


@pytest.fixture
def mock_deterministic(mocker):
    """Pin datetime.now to a fixed value for deterministic assertions."""
    mock_dt = mocker.patch("notificator.notificator.datetime")
    mock_dt.now.return_value = FIXED_DATETIME


@pytest.fixture
def notificator():
    return Notificator(org_id=ORG_ID)


@pytest.fixture
def mock_host_stream(mocker):
    """Mock the DB layer so methods that stream hosts can run without a real database.

    Unit/scenario tests mock the business-logic functions (``systems_by_app_stream``,
    ``get_relevant_systems``, ``packages_by_system``) so they never actually consume
    the stream.  This fixture simply makes the ``async for`` loops in the notificator
    methods execute once, yielding a dummy object that the mocked function ignores.
    """

    async def _fake_get_db():
        yield mocker.MagicMock()

    async def _fake_query_inventory(*args, **kwargs):
        yield mocker.MagicMock()

    mocker.patch("notificator.notificator.get_db", side_effect=lambda: _fake_get_db())
    mocker.patch(
        "notificator.notificator.query_host_inventory",
        side_effect=lambda *a, **kw: _fake_query_inventory(),
    )
