import pytest

from roadmap.sentry_config import before_send
from roadmap.sentry_config import has_filtered_message
from roadmap.sentry_config import has_filtered_message_dict
from roadmap.sentry_config import is_http_exception
from roadmap.sentry_config import is_http_exception_dict
from roadmap.sentry_config import should_filter_event


class HTTPException(Exception):
    """Mock HTTPException for testing."""

    pass


class OtherException(Exception):
    """Mock non-HTTP exception for testing."""

    pass


def test_before_send_filters_http_exception_with_filtered_message():
    """Test that HTTPException with filtered message is blocked."""
    event = {
        "exception": {
            "values": [
                {
                    "type": "HTTPException",
                    "value": "Not authorized to access host inventory",
                }
            ]
        }
    }
    hint = {}

    result = before_send(event, hint)

    assert result is None


def test_before_send_filters_http_exception_with_not_found():
    """Test that HTTPException with 'Not Found' message is blocked."""
    event = {
        "exception": {
            "values": [
                {
                    "type": "HTTPException",
                    "value": "Not Found",
                }
            ]
        }
    }
    hint = {}

    result = before_send(event, hint)

    assert result is None


def test_before_send_allows_http_exception_with_other_message():
    """Test that HTTPException with non-filtered message is allowed."""
    event = {
        "exception": {
            "values": [
                {
                    "type": "HTTPException",
                    "value": "Internal Server Error",
                }
            ]
        }
    }
    hint = {}

    result = before_send(event, hint)

    assert result == event


def test_before_send_allows_non_http_exception():
    """Test that non-HTTPException is allowed through."""
    event = {
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "Not authorized to access host inventory",
                }
            ]
        }
    }
    hint = {}

    result = before_send(event, hint)

    assert result == event


def test_before_send_filters_via_exc_info_in_hint():
    """Test filtering works when exception is in hint's exc_info."""
    event = {}
    hint = {
        "exc_info": (
            HTTPException,
            HTTPException("Not authorized to access host inventory"),
            None,
        )
    }

    result = before_send(event, hint)

    assert result is None


def test_before_send_allows_via_exc_info_with_different_message():
    """Test non-filtered message in hint's exc_info is allowed."""
    event = {}
    hint = {
        "exc_info": (
            HTTPException,
            HTTPException("Something else went wrong"),
            None,
        )
    }

    result = before_send(event, hint)

    assert result == event


def test_before_send_allows_non_http_exception_in_hint():
    """Test non-HTTPException in hint is allowed."""
    event = {}
    hint = {
        "exc_info": (
            OtherException,
            OtherException("Not authorized to access host inventory"),
            None,
        )
    }

    result = before_send(event, hint)

    assert result == event


def test_before_send_with_empty_event_and_hint():
    """Test that empty event and hint is allowed through."""
    event = {}
    hint = {}

    result = before_send(event, hint)

    assert result == event


def test_is_http_exception_with_http_exception():
    """Test HTTPException is correctly identified."""
    assert is_http_exception(HTTPException) is True


def test_is_http_exception_with_other_exception():
    """Test non-HTTPException is correctly identified."""
    assert is_http_exception(ValueError) is False


def test_is_http_exception_with_none():
    """Test None is handled correctly."""
    assert is_http_exception(None) is False


def test_has_filtered_message_with_filtered_message():
    """Test filtered message is correctly identified."""
    exc = HTTPException("Not authorized to access host inventory")
    assert has_filtered_message(exc) is True


def test_has_filtered_message_with_not_found():
    """Test 'Not Found' message is correctly identified."""
    exc = HTTPException("Not Found")
    assert has_filtered_message(exc) is True


def test_has_filtered_message_with_partial_match():
    """Test partial match of filtered message."""
    exc = HTTPException("Error: Not authorized to access host inventory - please contact support")
    assert has_filtered_message(exc) is True


def test_has_filtered_message_with_non_filtered_message():
    """Test non-filtered message is correctly identified."""
    exc = HTTPException("Internal Server Error")
    assert has_filtered_message(exc) is False


def test_has_filtered_message_with_none():
    """Test None is handled correctly."""
    assert has_filtered_message(None) is False


def test_is_http_exception_dict_with_http_exception():
    """Test HTTPException dict is correctly identified."""
    exception = {"type": "HTTPException", "value": "some error"}
    assert is_http_exception_dict(exception) is True


def test_is_http_exception_dict_with_partial_match():
    """Test HTTPException in type name is matched."""
    exception = {"type": "fastapi.HTTPException", "value": "some error"}
    assert is_http_exception_dict(exception) is True


def test_is_http_exception_dict_with_other_exception():
    """Test non-HTTPException dict is correctly identified."""
    exception = {"type": "ValueError", "value": "some error"}
    assert is_http_exception_dict(exception) is False


def test_is_http_exception_dict_with_missing_type():
    """Test dict without type is handled correctly."""
    exception = {"value": "some error"}
    assert is_http_exception_dict(exception) is False


def test_is_http_exception_dict_with_empty_dict():
    """Test empty dict is handled correctly."""
    exception = {}
    assert is_http_exception_dict(exception) is False


def test_has_filtered_message_dict_with_filtered_message():
    """Test filtered message in dict is correctly identified."""
    exception = {"type": "HTTPException", "value": "Not authorized to access host inventory"}
    assert has_filtered_message_dict(exception) is True


def test_has_filtered_message_dict_with_not_found():
    """Test 'Not Found' in dict is correctly identified."""
    exception = {"type": "HTTPException", "value": "Not Found"}
    assert has_filtered_message_dict(exception) is True


def test_has_filtered_message_dict_with_non_filtered_message():
    """Test non-filtered message in dict is correctly identified."""
    exception = {"type": "HTTPException", "value": "Internal Server Error"}
    assert has_filtered_message_dict(exception) is False


def test_has_filtered_message_dict_with_missing_value():
    """Test dict without value is handled correctly."""
    exception = {"type": "HTTPException"}
    assert has_filtered_message_dict(exception) is False


def test_should_filter_event_with_multiple_exceptions():
    """Test filtering works when event has multiple exceptions."""
    event = {
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "Some other error",
                },
                {
                    "type": "HTTPException",
                    "value": "Not authorized to access host inventory",
                },
            ]
        }
    }
    hint = {}

    assert should_filter_event(event, hint) is True


def test_should_filter_event_with_no_filtered_exceptions():
    """Test no filtering when no exceptions match."""
    event = {
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "Some error",
                },
                {
                    "type": "KeyError",
                    "value": "Some key",
                },
            ]
        }
    }
    hint = {}

    assert should_filter_event(event, hint) is False


def test_before_send_with_partial_message_match():
    """Test that partial message matching works."""
    event = {
        "exception": {
            "values": [
                {
                    "type": "HTTPException",
                    "value": "403: Not authorized to access host inventory for this account",
                }
            ]
        }
    }
    hint = {}

    result = before_send(event, hint)

    assert result is None
