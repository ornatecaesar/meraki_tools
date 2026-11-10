"""Shared building blocks used by every tool in the package.

Import from here rather than from the individual modules::

    from meraki_tools.core import get_dashboard, get_organization_id, setup_logging
"""

from meraki_tools.core.action_batch import ActionBatcher
from meraki_tools.core.client import MissingAPIKeyError, get_dashboard
from meraki_tools.core.errors import format_api_error
from meraki_tools.core.logging_setup import setup_logging
from meraki_tools.core.organizations import (
    OrganizationSelectionError,
    get_organization_id,
)
from meraki_tools.core.vlans import (
    add_vlan_to_list,
    format_vlan_list,
    is_vlan_in_list,
    parse_vlan_list,
    remove_vlan_from_list,
)

__all__ = [
    "ActionBatcher",
    "MissingAPIKeyError",
    "OrganizationSelectionError",
    "add_vlan_to_list",
    "format_api_error",
    "format_vlan_list",
    "get_dashboard",
    "get_organization_id",
    "is_vlan_in_list",
    "parse_vlan_list",
    "remove_vlan_from_list",
    "setup_logging",
]
