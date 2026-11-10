"""Helpers for reporting errors from the Meraki library."""

from __future__ import annotations

import meraki


def format_api_error(error: meraki.APIError) -> str:
    """Return a one-line, human-readable summary of a Dashboard API error.

    Args:
        error: The exception raised by the ``meraki`` library.

    Returns:
        A string such as ``"switch/getDeviceSwitchPorts failed: 404 Not Found - ..."``.
    """
    detail = f" - {error.message}" if error.message else ""
    return f"{error.tag}/{error.operation} failed: {error.status} {error.reason}{detail}"
