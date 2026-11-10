"""Work out which Meraki organisation a tool should act on."""

from __future__ import annotations

import os

import meraki

#: Environment variable that pins the organisation ID when the API key can see
#: more than one organisation.
ORG_ID_ENV_VAR = "MERAKI_ORG_ID"


class OrganizationSelectionError(RuntimeError):
    """Raised when the organisation to use cannot be determined safely."""


def get_organization_id(dashboard: meraki.DashboardAPI, org_id: str | None = None) -> str:
    """Return the ID of the organisation to work on.

    The old scripts always used the first organisation returned by the API,
    which silently picks the wrong one when a key has access to several. This
    function only guesses when there is exactly one choice.

    Resolution order:

    1. ``org_id`` if given.
    2. The ``MERAKI_ORG_ID`` environment variable if set.
    3. The only organisation the API key can access.

    Args:
        dashboard: Dashboard API client.
        org_id: Explicit organisation ID, usually from a ``--org-id`` option.

    Returns:
        The organisation ID.

    Raises:
        OrganizationSelectionError: If the key can access no organisations, or
            several and none was chosen.
    """
    chosen = org_id or os.environ.get(ORG_ID_ENV_VAR)
    if chosen:
        return chosen

    organizations = dashboard.organizations.getOrganizations(total_pages="all")
    if len(organizations) == 1:
        return organizations[0]["id"]
    if not organizations:
        raise OrganizationSelectionError("This API key does not have access to any organisations.")

    choices = ", ".join(f"{org['name']} ({org['id']})" for org in organizations)
    raise OrganizationSelectionError(
        f"This API key can access {len(organizations)} organisations: {choices}. "
        f"Choose one with --org-id or the {ORG_ID_ENV_VAR} environment variable."
    )
