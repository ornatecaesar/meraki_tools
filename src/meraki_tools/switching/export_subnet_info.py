"""Export every layer 3 interface (SVI) on your switches and switch stacks to CSV.

For each routed interface it records the network, switch or stack, interface
name, VLAN, subnet and interface IP. Stack members are covered by their
stack's interfaces, so they are not queried individually. Switches that do
not do layer 3 routing are skipped.

The CSV is written to ``output/export_subnet_info/l3_interfaces_<date>.csv``.

Example:
    meraki-tools export-subnet-info --network College
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

import meraki

from meraki_tools.core.cli import ToolContext, base_parser, run_tool
from meraki_tools.core.errors import format_api_error
from meraki_tools.core.output import dated_output_path, format_table, write_csv

TOOL_NAME = "export_subnet_info"
COLUMNS = ["network", "switch", "name", "vlanId", "subnet", "interfaceIp", "defaultGateway"]


def interface_rows(interfaces: list[dict[str, Any]], *, network: str, switch: str) -> list[dict[str, Any]]:
    """Return one CSV row per routed interface.

    Args:
        interfaces: Interfaces from the Dashboard API.
        network: Network name to record against each row.
        switch: Switch or stack name to record against each row.
    """
    return [
        {
            "network": network,
            "switch": switch,
            **{key: interface.get(key) for key in COLUMNS[2:]},
        }
        for interface in interfaces
    ]


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__)
    parser.add_argument(
        "--network",
        metavar="TEXT",
        help="only networks whose name contains TEXT (case-insensitive)",
    )
    parser.add_argument("--show", action="store_true", help="also print the table to the console")
    return parser


def run(context: ToolContext) -> int:
    """Collect routed interfaces from every switch and stack, then write the CSV."""
    dashboard, org_id, args, log = context.dashboard, context.organization_id, context.args, context.logger

    networks = dashboard.organizations.getOrganizationNetworks(
        org_id, productTypes=["switch"], total_pages="all"
    )
    if args.network:
        networks = [n for n in networks if args.network.lower() in n["name"].lower()]
    switches = dashboard.organizations.getOrganizationDevices(
        org_id, productTypes=["switch"], total_pages="all"
    )

    rows: list[dict[str, Any]] = []
    for network in sorted(networks, key=lambda n: n["name"].lower()):
        stacks = dashboard.switch.getNetworkSwitchStacks(network["id"])
        stacked = {serial for stack in stacks for serial in stack.get("serials", [])}

        for stack in stacks:
            interfaces = dashboard.switch.getNetworkSwitchStackRoutingInterfaces(network["id"], stack["id"])
            rows += interface_rows(interfaces, network=network["name"], switch=stack["name"])

        for switch in switches:
            if switch.get("networkId") != network["id"] or switch["serial"] in stacked:
                continue
            name = switch.get("name") or switch["serial"]
            try:
                interfaces = dashboard.switch.getDeviceSwitchRoutingInterfaces(switch["serial"])
            except meraki.APIError as error:
                # Layer 2-only models reject this call; nothing to export for them.
                log.debug("Skipping %s: %s", name, format_api_error(error))
                continue
            rows += interface_rows(interfaces, network=network["name"], switch=name)

    path = write_csv(rows, COLUMNS, dated_output_path(TOOL_NAME, "l3_interfaces", ".csv"))
    log.info("Exported %d interfaces from %d networks to %s", len(rows), len(networks), path)
    if args.show and rows:
        print(format_table(rows, COLUMNS))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
