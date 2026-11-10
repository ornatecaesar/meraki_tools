r"""Turn tagged desk ports into trunks for desk-mounted wireless access points.

Finds every port carrying a given tag (for example ``DL_DESK``) and sets it to
a PoE trunk with the native and allowed VLANs an access point needs. Ports
that already match are skipped.

Examples:
    Preview the change for ports tagged DL_DESK on switches tagged IT:

        meraki-tools desk-port-to-wifi-trunk --port-tag DL_DESK --switch-tag IT \\
            --native-vlan 16 --allowed-vlans 16,150,700-701,790

    Apply it in networks whose name contains "College":

        meraki-tools desk-port-to-wifi-trunk --port-tag DL_DESK --native-vlan 16 \\
            --allowed-vlans 16,150,700-701,790 --network College --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from meraki_tools.core import ActionBatcher
from meraki_tools.core.cli import (
    ToolContext,
    add_switch_filters,
    base_parser,
    finish_changes,
    run_tool,
    vlan_id,
)
from meraki_tools.core.switches import Port, iter_switch_ports, port_resource
from meraki_tools.core.vlans import format_vlan_list, parse_vlan_list

TOOL_NAME = "set_desk_port_to_wifi_trunk"


def trunk_settings(native_vlan: int, allowed_vlans: str) -> dict[str, Any]:
    """Return the port settings for an access point trunk."""
    return {
        "enabled": True,
        "poeEnabled": True,
        "type": "trunk",
        "vlan": native_vlan,
        "allowedVlans": allowed_vlans,
    }


def needs_change(port: Port, settings: dict[str, Any]) -> bool:
    """Return whether a port's configuration differs from the target settings.

    ``allowedVlans`` is compared as a set of VLANs, so ``"700,701"`` and
    ``"700-701"`` count as the same.
    """
    for key, value in settings.items():
        if key == "allowedVlans":
            if parse_vlan_list(port.get(key) or "") != parse_vlan_list(value):
                return True
        elif port.get(key) != value:
            return True
    return False


def allowed_vlans_arg(value: str) -> str:
    """Argparse type that validates and normalises an allowed VLAN list."""
    try:
        vlans = parse_vlan_list(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None
    if vlans is None:
        return "all"
    if not vlans:
        raise argparse.ArgumentTypeError("the allowed VLAN list is empty")
    return format_vlan_list(vlans)


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__, changes_config=True)
    parser.add_argument("--port-tag", required=True, help="change ports that have this tag")
    parser.add_argument("--switch-tag", help="only look at switches that have this device tag")
    parser.add_argument(
        "--native-vlan", type=vlan_id, required=True, metavar="VLAN", help="native (untagged) VLAN"
    )
    parser.add_argument(
        "--allowed-vlans",
        type=allowed_vlans_arg,
        required=True,
        metavar="LIST",
        help='VLANs the trunk carries, for example "16,150,700-701"',
    )
    add_switch_filters(parser)
    return parser


def _switch_serials_with_tag(context: ToolContext, tag: str) -> set[str]:
    devices = context.dashboard.organizations.getOrganizationDevices(
        context.organization_id, productTypes=["switch"], tags=[tag], total_pages="all"
    )
    return {device["serial"] for device in devices}


def run(context: ToolContext) -> int:
    """Queue a trunk update for every tagged port that does not match yet."""
    args, log = context.args, context.logger
    settings = trunk_settings(args.native_vlan, args.allowed_vlans)
    tagged_switches = _switch_serials_with_tag(context, args.switch_tag) if args.switch_tag else None

    with ActionBatcher(context.dashboard, context.organization_id, dry_run=context.dry_run) as batcher:
        for switch, ports in iter_switch_ports(
            context.dashboard, context.organization_id, network=args.network, switch_name=args.switch
        ):
            if tagged_switches is not None and switch.serial not in tagged_switches:
                continue
            for port in ports:
                if args.port_tag not in (port.get("tags") or []) or not needs_change(port, settings):
                    continue
                log.info(
                    "%s port %s (%s): trunk, native %s, allowed %s",
                    switch.name,
                    port["portId"],
                    port.get("name") or "unnamed",
                    args.native_vlan,
                    args.allowed_vlans,
                )
                batcher.update(port_resource(switch.serial, port["portId"]), settings)

    return finish_changes(context, batcher, "desk ports")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
