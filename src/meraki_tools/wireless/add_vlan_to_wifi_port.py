"""Add a VLAN to every switch trunk that carries access point traffic.

Use this when a new SSID with its own VLAN is added, so that the VLAN reaches
every access point. Ports that already allow the VLAN are skipped.

See :mod:`meraki_tools.wireless.ap_trunks` for how ports are chosen.

Examples:
    Preview adding VLAN 790 to AP ports (native VLAN 16) and the uplinks
    between switches (native VLAN 1001):

        meraki-tools add-vlan-to-ap-trunks 790 --ap-vlan 16 --uplink-native-vlan 1001

    Apply it on switches whose name contains "SW-ARK":

        meraki-tools add-vlan-to-ap-trunks 790 --ap-vlan 16 --switch SW-ARK --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from meraki_tools.core import ActionBatcher
from meraki_tools.core.cli import ToolContext, finish_changes, run_tool
from meraki_tools.core.switches import iter_switch_ports, port_resource
from meraki_tools.core.vlans import add_vlan_to_list
from meraki_tools.wireless import ap_trunks

TOOL_NAME = "add_vlan_to_wifi_port"


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    return ap_trunks.build_parser(__doc__)


def run(context: ToolContext) -> int:
    """Queue an update for every access point trunk that lacks the VLAN."""
    args, log = context.args, context.logger

    with ActionBatcher(context.dashboard, context.organization_id, dry_run=context.dry_run) as batcher:
        for switch, ports in iter_switch_ports(
            context.dashboard, context.organization_id, network=args.network, switch_name=args.switch
        ):
            for port in ports:
                if not ap_trunks.is_ap_trunk(port, args.ap_vlan, args.uplink_native_vlan):
                    continue
                old = port["allowedVlans"]
                new = add_vlan_to_list(args.vlan, old)
                if new == old:
                    continue
                log.info("%s port %s: allowed VLANs %s -> %s", switch.name, port["portId"], old, new)
                batcher.update(port_resource(switch.serial, port["portId"]), {"allowedVlans": new})

    return finish_changes(context, batcher, "trunk ports")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
