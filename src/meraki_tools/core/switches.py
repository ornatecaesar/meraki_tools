"""Fetch switches and their port configuration across an organisation.

The original scripts walked organisation → networks → devices → ports, making
one API call per switch. :func:`iter_switch_ports` gets the same information
from a single paginated organisation-wide endpoint, which is far quicker on
large estates and much lighter on the rate limit.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import meraki

#: A port's configuration as returned by the Dashboard API.
Port = dict[str, Any]


@dataclass(frozen=True)
class Switch:
    """The identifying details of a switch.

    Attributes:
        serial: Device serial number.
        name: Device name as shown in the Dashboard (falls back to the serial).
        model: Hardware model, for example ``"MS120-8FP"``.
        network_id: ID of the network the switch belongs to.
        network_name: Name of that network.
    """

    serial: str
    name: str
    model: str
    network_id: str
    network_name: str

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Switch:
        """Build a :class:`Switch` from one ``getOrganizationSwitchPortsBySwitch`` item."""
        network = item.get("network") or {}
        return cls(
            serial=item["serial"],
            name=item.get("name") or item["serial"],
            model=item.get("model", ""),
            network_id=network.get("id", ""),
            network_name=network.get("name", ""),
        )


def port_resource(serial: str, port_id: str) -> str:
    """Return the action batch resource path for one switch port."""
    return f"/devices/{serial}/switch/ports/{port_id}"


def find_network_ids(dashboard: meraki.DashboardAPI, organization_id: str, name_contains: str) -> list[str]:
    """Return the IDs of switch networks whose name contains some text.

    Args:
        dashboard: Dashboard API client.
        organization_id: Organisation to search.
        name_contains: Case-insensitive text to look for in the network name.

    Returns:
        Matching network IDs. Empty if nothing matches.
    """
    networks = dashboard.organizations.getOrganizationNetworks(
        organization_id, productTypes=["switch"], total_pages="all"
    )
    needle = name_contains.lower()
    return [network["id"] for network in networks if needle in network["name"].lower()]


def iter_switch_ports(
    dashboard: meraki.DashboardAPI,
    organization_id: str,
    *,
    network: str | None = None,
    switch_name: str | None = None,
) -> Iterator[tuple[Switch, list[Port]]]:
    """Yield every switch in the organisation with its port configuration.

    Args:
        dashboard: Dashboard API client.
        organization_id: Organisation to read.
        network: Only include switches in networks whose name contains this
            text (case-insensitive).
        switch_name: Only include switches whose name contains this text.
            The Dashboard does this match, case-insensitively.

    Yields:
        ``(switch, ports)`` pairs, sorted by switch name.
    """
    filters: dict[str, Any] = {}
    if switch_name:
        filters["name"] = switch_name
    if network:
        network_ids = find_network_ids(dashboard, organization_id, network)
        if not network_ids:
            return
        filters["networkIds"] = network_ids

    items = dashboard.switch.getOrganizationSwitchPortsBySwitch(organization_id, total_pages="all", **filters)
    for item in sorted(items, key=lambda i: (i.get("name") or i["serial"]).lower()):
        yield Switch.from_api(item), item.get("ports", [])
