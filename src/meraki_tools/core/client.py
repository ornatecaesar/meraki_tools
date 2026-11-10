"""Create a configured Meraki Dashboard API client.

Every tool gets its client from :func:`get_dashboard` so that the API key
handling, logging behaviour and retry settings are the same everywhere.
"""

from __future__ import annotations

import os

import meraki

from meraki_tools import __version__

#: Environment variable that holds the Dashboard API key.
API_KEY_ENV_VAR = "MERAKI_API_KEY"

#: Identifies these tools to Meraki in the API's ``User-Agent`` header, using
#: the ``ApplicationName VendorName`` format Meraki asks integrations to send.
CALLER = f"MerakiTools/{__version__} ornatecaesar"


class MissingAPIKeyError(RuntimeError):
    """Raised when no API key is passed in and none is set in the environment."""


def get_dashboard(
    api_key: str | None = None,
    *,
    simulate: bool = False,
    maximum_retries: int = 5,
) -> meraki.DashboardAPI:
    """Return a Dashboard API client configured the same way for every tool.

    The client sends its log records through Python's standard :mod:`logging`
    module (configure it with :func:`meraki_tools.core.setup_logging`) rather
    than writing its own log files into the working directory or printing to
    the console.

    Args:
        api_key: Dashboard API key. Defaults to the ``MERAKI_API_KEY``
            environment variable, which is the recommended way to supply it
            so the key never ends up in source code or shell history.
        simulate: When ``True`` the library logs the requests that would
            change configuration (POST, PUT and DELETE) without sending them.
            Read requests still go to the API.
        maximum_retries: How many times to retry a request that fails with a
            rate limit (429) or server (5xx) error.

    Returns:
        A ready-to-use :class:`meraki.DashboardAPI` instance.

    Raises:
        MissingAPIKeyError: If no API key is available.
    """
    key = api_key or os.environ.get(API_KEY_ENV_VAR)
    if not key:
        raise MissingAPIKeyError(
            f"No Meraki API key found. Set the {API_KEY_ENV_VAR} environment "
            "variable (in PyCharm: Run > Edit Configurations > Environment "
            "variables) or pass api_key explicitly."
        )

    return meraki.DashboardAPI(
        api_key=key,
        caller=CALLER,
        simulate=simulate,
        maximum_retries=maximum_retries,
        wait_on_rate_limit=True,
        # Route the library's log records through our own logging setup.
        output_log=False,
        print_console=False,
        inherit_logging_config=True,
    )
