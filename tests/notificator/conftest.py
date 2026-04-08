import pytest

from notificator.notificator import Notificator
from roadmap.config import Settings

from .utils import FIXED_DATETIME
from .utils import FIXED_UUID
from .utils import ORG_ID


@pytest.fixture(autouse=True)
def clear_settings_cache():
    Settings.create.cache_clear()
    yield
    Settings.create.cache_clear()


@pytest.fixture
def mock_deterministic(mocker):
    """Pin uuid4 and datetime.now to fixed values for deterministic assertions."""
    mocker.patch("notificator.notificator.uuid4", return_value=FIXED_UUID)
    mock_dt = mocker.patch("notificator.notificator.datetime")
    mock_dt.now.return_value = FIXED_DATETIME


@pytest.fixture
def notificator():
    return Notificator(org_id=ORG_ID)
