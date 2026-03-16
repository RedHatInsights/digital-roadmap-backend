"""
Configures Sentry/Glitchtip filtering to exclude noisy or expected exceptions.
"""

from typing import Optional

from sentry_sdk.types import Event
from sentry_sdk.types import Hint


FILTERED_EXCEPTION_MESSAGES = [
    "Not authorized to access host inventory",
    "Not Found",
]


def before_send(event: Event, hint: Hint) -> Optional[Event]:
    """
    Filter out specific exceptions from being sent to Sentry/Glitchtip.

    Args:
        event: The Sentry event to potentially filter
        hint: Additional context about the event

    Returns:
        None to filter out the event, or the event to send it
    """
    if should_filter_event(event, hint):
        return None  # Don't send this event to Glitchtip

    return event  # Send the event


def should_filter_event(event: Event, hint: Hint) -> bool:
    """
    Determine if an event should be filtered based on exception type and message.

    Args:
        event: The Sentry event to check
        hint: Additional context about the event

    Returns:
        True if the event should be filtered, False otherwise
    """
    # Check if there's an exception in the hint
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]

        # Filter HTTPException with specific messages
        if is_http_exception(exc_type) and has_filtered_message(exc_value):
            return True

    # Also check exception values in the event itself
    if "exception" in event and "values" in event["exception"]:
        for exception in event["exception"]["values"]:
            if is_http_exception_dict(exception) and has_filtered_message_dict(exception):
                return True

    return False


def is_http_exception(exc_type) -> bool:
    """
    Check if the exception type is an HTTPException.

    Args:
        exc_type: The exception type to check

    Returns:
        True if it's an HTTPException, False otherwise
    """
    if exc_type is None:
        return False

    exc_type_name = exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type)
    return "HTTPException" in exc_type_name


def has_filtered_message(exc_value) -> bool:
    """
    Check if the exception value contains a filtered message.

    Args:
        exc_value: The exception value to check

    Returns:
        True if it contains a filtered message, False otherwise
    """
    if exc_value is None:
        return False

    exc_message = str(exc_value)
    return any(filtered_msg in exc_message for filtered_msg in FILTERED_EXCEPTION_MESSAGES)


def is_http_exception_dict(exception: dict) -> bool:
    """
    Check if the exception dict represents an HTTPException.

    Args:
        exception: The exception dictionary from Sentry event

    Returns:
        True if it's an HTTPException, False otherwise
    """
    exc_type = exception.get("type")
    return bool(exc_type and "HTTPException" in exc_type)


def has_filtered_message_dict(exception: dict) -> bool:
    """
    Check if the exception dict contains a filtered message.

    Args:
        exception: The exception dictionary from Sentry event

    Returns:
        True if it contains a filtered message, False otherwise
    """
    exc_message = exception.get("value", "")
    return any(filtered_msg in exc_message for filtered_msg in FILTERED_EXCEPTION_MESSAGES)
