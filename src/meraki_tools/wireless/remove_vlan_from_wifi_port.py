"""Remove a VLAN from every switch trunk that carries access point traffic.

Use this when an SSID's VLAN is retired. Ranges are split where needed (for
example removing 45 from ``40-50`` leaves ``40-44,46-50``). Ports that do not
carry the VLAN are skipped, and a port is never left with an empty list.

See :mod:`meraki_tools.wireless.ap_trunks` for how ports are chosen.

Examples:
    Preview removing VLAN 45:

        meraki-tools remove-vlan-from-ap-trunks 45 --ap-vlan 16 --uplink-native-vlan 1001

    Apply it on switches whose name contains "SW-LB":

        meraki-tools remove-vlan-from-ap-trunks 45 --ap-vlan 16 --switch SW-LB --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from meraki_tools.core import ActionBatcher
from meraki_tools.core.cli import ToolContext, finish_changes, run_tool
from meraki_tools.core.switches import iter_switch_ports, port_resource
from meraki_tools.core.vlans import remove_vlan_from_list
from meraki_tools.wireless import ap_trunks

TOOL_NAME = "remove_vlan_from_wifi_port"


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    return ap_trunks.build_parser(__doc__)


def run(context: ToolContext) -> int:
    """Queue an update for every access point trunk that carries the VLAN."""
    args, log = context.args, context.logger
    if args.vlan == args.ap_vlan:
        log.error("Refusing to remove the access point management VLAN (%d) itself", args.vlan)
        return 2

    with ActionBatcher(context.dashboard, context.organization_id, dry_run=context.dry_run) as batcher:
        for switch, ports in iter_switch_ports(
            context.dashboard, context.organization_id, network=args.network, switch_name=args.switch
        ):
            for port in ports:
                if not ap_trunks.is_ap_trunk(port, args.ap_vlan, args.uplink_native_vlan):
                    continue
                old = port["allowedVlans"]
                new = remove_vlan_from_list(args.vlan, old)
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
