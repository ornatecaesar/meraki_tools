"""List every switch port that carries a VLAN.

A port carries the VLAN when it is:

* an access port on that VLAN (or using it as the voice VLAN), or
* a trunk with it as the native VLAN or in its allowed list.

Trunks that allow all VLANs technically carry every VLAN, so they are left
out unless you add ``--include-all-trunks``; otherwise every uplink would
appear in the results.

Examples:
    Show the ports carrying VLAN 100:

        meraki-tools find-ports-with-vlan 100

    Save them to a CSV in output/find_ports_with_vlan/:

        meraki-tools find-ports-with-vlan 100 --network Junior --csv
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from meraki_tools.core.cli import ToolContext, add_switch_filters, base_parser, run_tool, vlan_id
from meraki_tools.core.output import dated_output_path, format_table, write_csv
from meraki_tools.core.switches import Port, iter_switch_ports
from meraki_tools.core.vlans import parse_vlan_list

TOOL_NAME = "find_ports_with_vlan"
COLUMNS = ["network", "switch", "port", "name", "type", "native_vlan", "allowed_vlans", "match"]


def match_reason(port: Port, vlan: int, *, include_all_trunks: bool = False) -> str | None:
    """Return why a port carries the VLAN, or ``None`` if it does not.

    Args:
        port: Port configuration from the Dashboard API.
        vlan: The VLAN to look for.
        include_all_trunks: Count trunks whose allowed list is ``"all"``.

    Returns:
        A short reason such as ``"access"``, ``"voice"``, ``"native"``,
        ``"allowed"`` or ``"allowed (all)"``, or ``None``.
    """
    if port.get("type") == "access":
        if port.get("vlan") == vlan:
            return "access"
        return "voice" if port.get("voiceVlan") == vlan else None

    if port.get("type") != "trunk":
        return None
    allowed = parse_vlan_list(port.get("allowedVlans") or "")
    if allowed is None:
        return "allowed (all)" if include_all_trunks else None
    if port.get("vlan") == vlan:
        return "native"
    return "allowed" if vlan in allowed else None


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__)
    parser.add_argument("vlan", type=vlan_id, help="VLAN ID to look for")
    parser.add_argument(
        "--include-all-trunks", action="store_true", help='also list trunks that allow "all" VLANs'
    )
    parser.add_argument("--csv", action="store_true", help="also save the results to a CSV file")
    add_switch_filters(parser)
    return parser


def run(context: ToolContext) -> int:
    """Find the matching ports and print or save them."""
    args, log = context.args, context.logger
    rows = []
    for switch, ports in iter_switch_ports(
        context.dashboard, context.organization_id, network=args.network, switch_name=args.switch
    ):
        for port in ports:
            reason = match_reason(port, args.vlan, include_all_trunks=args.include_all_trunks)
            if reason:
                rows.append(
                    {
                        "network": switch.network_name,
                        "switch": switch.name,
                        "port": port["portId"],
                        "name": port.get("name"),
                        "type": port.get("type"),
                        "native_vlan": port.get("vlan"),
                        "allowed_vlans": port.get("allowedVlans") if port.get("type") == "trunk" else "",
                        "match": reason,
                    }
                )

    log.info("Found %d ports carrying VLAN %d", len(rows), args.vlan)
    if rows:
        print(format_table(rows, COLUMNS))
    if args.csv:
        path = write_csv(rows, COLUMNS, dated_output_path(TOOL_NAME, f"vlan_{args.vlan}_ports", ".csv"))
        log.info("Saved %s", path)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
