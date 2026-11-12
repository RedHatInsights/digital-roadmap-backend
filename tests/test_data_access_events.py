"""The data.access event recorded when an org's host inventory is read.

Kept separate from tests/test_audit.py, which covers the audit module itself
rather than the dependency that emits this particular event.
"""

import pytest
import structlog

from sqlalchemy.exc import DBAPIError

from roadmap.audit import ACTION_DATA_ACCESS
from roadmap.audit import RESULT_FAILURE
from roadmap.audit import RESULT_SUCCESS
from roadmap.common import query_host_inventory
from roadmap.common import query_rhel_systems
from roadmap.config import Settings
from roadmap.models import LifecycleType


@pytest.fixture
def capture_events():
    with structlog.testing.capture_logs() as events:
        yield events


def access_events(events):
    return [event for event in events if event.get("action") == ACTION_DATA_ACCESS]


class FakeSession:
    """Minimal stand-in for AsyncSession.stream()."""

    def __init__(self, error=None):
        self._error = error

    async def stream(self, *args, **kwargs):
        if self._error is not None:
            raise self._error

        return "rows"


async def read_inventory(session):
    """Drive the dependency the way FastAPI does, to completion."""
    generator = query_host_inventory(
        org_id="12345",
        session=session,
        settings=Settings(),
        host_groups=set(),
    )
    results = [result async for result in generator]

    return results


class TestDataAccessEvent:
    async def test_opening_the_stream_is_recorded_as_stream_created(self, capture_events):
        """The rows are streamed, so a success here means the stream was
        opened -- not that the caller read it to the end."""
        await read_inventory(FakeSession())

        (event,) = access_events(capture_events)
        assert event["result"] == RESULT_SUCCESS
        assert event["phase"] == "stream-created"
        assert event["resource"] == "host_inventory"
        assert event["data_classification"] == "red-hat-restricted"

    async def test_failure_opening_the_stream_is_not_called_a_consumption_failure(self, capture_events):
        """A query that fails outright never reached any data. Recording it as
        a consumption failure would say an access began when it never did."""
        session = FakeSession(error=DBAPIError("SELECT 1", {}, Exception("boom")))

        with pytest.raises(Exception):
            await read_inventory(session)

        (event,) = access_events(capture_events)
        assert event["result"] == RESULT_FAILURE
        assert event["phase"] == "stream-open-failed"
        assert event["error_code"] == 500

    async def test_no_success_is_recorded_when_the_stream_never_opened(self, capture_events):
        """The success record must not be emitted at all on an open failure."""
        session = FakeSession(error=DBAPIError("SELECT 1", {}, Exception("boom")))

        with pytest.raises(Exception):
            await read_inventory(session)

        assert [event["result"] for event in access_events(capture_events)] == [RESULT_FAILURE]

    async def test_phase_distinguishes_the_two_records(self, capture_events):
        """One access that fails part-way emits both a success and a failure.
        Without phase they are an unqualified contradiction; with it, the
        pair reads as "opened, then failed while being read"."""
        generator = query_host_inventory(
            org_id="12345",
            session=FakeSession(),
            settings=Settings(),
            host_groups=set(),
        )
        await anext(generator)
        with pytest.raises(Exception):
            await generator.athrow(DBAPIError("SELECT 1", {}, Exception("boom")))

        phases = [(event["result"], event["phase"]) for event in access_events(capture_events)]
        assert phases == [
            (RESULT_SUCCESS, "stream-created"),
            (RESULT_FAILURE, "stream-consumed"),
        ]

    async def test_host_data_is_not_logged(self, capture_events):
        """The record says that an org's inventory was read, never what was in it."""
        await read_inventory(FakeSession())

        (event,) = access_events(capture_events)
        assert "rows" not in event.values()
        for field in ("hostname", "display_name", "packages", "search"):
            assert field not in event


class FakeResult:
    """Stand-in for the Result objects AsyncSession.execute() returns."""

    def __init__(self, rows=(), total=0):
        self._rows = list(rows)
        self._total = total

    def scalar(self):
        return self._total

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeExecuteSession:
    """AsyncSession.execute() for the paginated RHEL systems query.

    query_rhel_systems runs a count query and then a data query, in that
    order, so the two results are returned in sequence. Captures the bound
    parameters so a test can assert what did and did not reach the database.
    """

    def __init__(self, rows=(), total=0, error=None):
        self._results = [FakeResult(total=total), FakeResult(rows=rows)]
        self._error = error
        self.params = []

    async def execute(self, statement, params):
        self.params.append(params)
        if self._error is not None:
            raise self._error

        return self._results.pop(0)


async def read_rhel_systems(session, search=None):
    return await query_rhel_systems(
        org_id="12345",
        session=session,
        settings=Settings(),
        host_groups=set(),
        major=9,
        minor=4,
        lifecycle_type=LifecycleType.mainline,
        search=search,
    )


class TestRhelSystemsAccessEvent:
    """The second data.access call site, on the paginated RHEL systems read."""

    async def test_success_is_recorded_with_the_record_count(self, capture_events):
        rows = [
            {
                "id": "f770fbf4-359d-11f0-b21b-5e43c8b8aa2f",
                "display_name": "host-a",
                "os_major": 9,
                "os_minor": 4,
            }
        ]
        await read_rhel_systems(FakeExecuteSession(rows=rows, total=1))

        (event,) = access_events(capture_events)
        assert event["result"] == RESULT_SUCCESS
        assert event["record_count"] == 1
        assert event["resource"] == "host_inventory"
        assert event["data_classification"] == "red-hat-restricted"
        assert event["lifecycle_type"] == "mainline"

    async def test_failure_is_recorded_at_error(self, capture_events):
        session = FakeExecuteSession(error=DBAPIError("SELECT 1", {}, Exception("boom")))

        with pytest.raises(Exception):
            await read_rhel_systems(session)

        (event,) = access_events(capture_events)
        assert event["result"] == RESULT_FAILURE
        assert event["log_level"] == "error"
        assert event["error_code"] == 500

    async def test_searched_flag_is_recorded(self, capture_events):
        await read_rhel_systems(FakeExecuteSession(), search="prod-db")

        (event,) = access_events(capture_events)
        assert event["searched"] is True

    async def test_searched_is_false_without_a_search(self, capture_events):
        await read_rhel_systems(FakeExecuteSession())

        (event,) = access_events(capture_events)
        assert event["searched"] is False

    async def test_the_search_term_itself_is_never_logged(self, capture_events):
        """A search term may name a customer's systems, so only the boolean
        reaches the log. This is the PII guarantee in SECURITY_LOGGING.md §6;
        it had no test before."""
        term = "acct-4815162342-prod"
        session = FakeExecuteSession()

        await read_rhel_systems(session, search=term)

        (event,) = access_events(capture_events)
        # The term reached the database as a bound parameter...
        assert any(term in str(params.get("search_pattern", "")) for params in session.params)
        # ...and reached the audit record nowhere.
        assert term not in str(event)
        assert "search" not in event
        assert "search_pattern" not in event
