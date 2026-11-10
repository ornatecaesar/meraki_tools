"""Temporary stand-ins for the old top-level ``meraki_utils`` module.

The scripts moved into this package in the restructure still call these
functions. Each script is moved onto :mod:`meraki_tools.core` as it is reviewed
and refactored, and this module is deleted once nothing imports it.
"""

from __future__ import annotations

import meraki

from meraki_tools.core.client import get_dashboard


def connect_to_meraki(*_args: object, **_kwargs: object) -> meraki.DashboardAPI:
    """Return a Dashboard client. Deprecated: use :func:`meraki_tools.core.get_dashboard`.

    Any arguments are ignored. The old function took a ``print_console`` flag
    that scripts were passing the API key into by mistake.
    """
    return get_dashboard()


def meraki_error(error: meraki.APIError) -> str:
    """Describe a Dashboard API error. Deprecated: use :func:`meraki_tools.core.format_api_error`."""
    return (
        f"Meraki API error: {error}\n"
        f"\t- status code: {error.status}\n"
        f"\t- reason: {error.reason}\n"
        f"\t- message: {error.message}"
    )


def other_error(error: Exception) -> str:
    """Describe any other error. Deprecated: log the exception directly instead."""
    return f"Other error: {error}"
