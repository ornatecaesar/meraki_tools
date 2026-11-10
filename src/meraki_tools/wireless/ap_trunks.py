"""Shared logic for the tools that change the VLANs on access point trunks.

Meraki access points are usually connected to switch trunk ports whose native
VLAN is the wireless management VLAN, with the SSID VLANs tagged on top. The
uplinks between switches must carry the same VLANs, or clients on those SSIDs
lose connectivity.

:func:`is_ap_trunk` picks out both kinds of port so that a VLAN can be added
to, or removed from, every link the wireless traffic crosses in one run.
"""

from __future__ import annotations

import argparse

from meraki_tools.core.cli import add_switch_filters, base_parser, vlan_id
from meraki_tools.core.switches import Port
from meraki_tools.core.vlans import is_vlan_in_list, parse_vlan_list


def is_ap_trunk(port: Port, ap_vlan: int, uplink_native_vlan: int | None = None) -> bool:
    """Return whether a port is a trunk that carries access point traffic.

    Args:
        port: Port configuration from the Dashboard API.
        ap_vlan: The wireless management VLAN, used as the native VLAN on
            access point ports.
        uplink_native_vlan: Native VLAN of switch-to-switch uplinks. When
            given, uplinks with this native VLAN that carry ``ap_vlan`` are
            included too.

    Returns:
        ``True`` for an access point trunk (native VLAN ``ap_vlan``) or a
        matching uplink. Trunks that allow all VLANs are never included,
        because they already carry every VLAN and cannot have one removed.
    """
    if port.get("type") != "trunk":
        return False
    allowed = port.get("allowedVlans") or ""
    if parse_vlan_list(allowed) is None:
        return False
    if port.get("vlan") == ap_vlan:
        return True
    return (
        uplink_native_vlan is not None
        and port.get("vlan") == uplink_native_vlan
        and is_vlan_in_list(ap_vlan, allowed)
    )


def build_parser(description: str | None) -> argparse.ArgumentParser:
    """Return the argument parser shared by the add and remove tools."""
    parser = base_parser(description, changes_config=True)
    parser.add_argument("vlan", type=vlan_id, help="the VLAN to add or remove")
    parser.add_argument(
        "--ap-vlan",
        type=vlan_id,
        required=True,
        metavar="VLAN",
        help="wireless management VLAN, the native VLAN on access point ports",
    )
    parser.add_argument(
        "--uplink-native-vlan",
        type=vlan_id,
        metavar="VLAN",
        help="also change switch-to-switch trunks with this native VLAN that carry --ap-vlan",
    )
    add_switch_filters(parser)
    return parser
