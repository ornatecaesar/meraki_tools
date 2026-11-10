"""Snapshot every switch port's traffic, status and neighbour, and list the busiest.

For each port it records status, speed, duplex, average traffic over the
look-back period (in Mbps, from the API's ``trafficInKbps``), total data
used, client count, error and warning counts, and the CDP/LLDP neighbour.
The busiest ports are printed; ``--csv`` saves every port to
``output/port_status_snapshot/port_status_<date>.csv``.

Examples:
    Top 20 busiest ports over the last day:

        meraki-tools port-status-snapshot

    Top 10 over the last week in one network, and save everything to CSV:

        meraki-tools port-status-snapshot --hours 168 --top 10 --network College --csv
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import meraki

from meraki_tools.core.cli import ToolContext, add_switch_filters, base_parser, run_tool
from meraki_tools.core.errors import format_api_error
from meraki_tools.core.output import dated_output_path, format_table, write_csv
from meraki_tools.core.switches import find_network_ids

TOOL_NAME = "port_status_snapshot"
MAX_HOURS = 31 * 24

COLUMNS = [
    "timestamp",
    "network",
    "switch",
    "serial",
    "port",
    "enabled",
    "status",
    "speed",
    "duplex",
    "recv_mbps",
    "sent_mbps",
    "total_mbps",
    "usage_kb",
    "clients",
    "errors",
    "warnings",
    "neighbour",
]
TOP_COLUMNS = ["switch", "port", "status", "speed", "total_mbps", "neighbour"]


def neighbour_of(port: dict[str, Any]) -> str:
    """Return ``"device:port"`` for the port's CDP or LLDP neighbour, or ``""``.

    Example:
        >>> neighbour_of({"lldp": {"systemName": "AP-01", "portId": "eth0"}})
        'AP-01:eth0'
    """
    info = port.get("cdp") or port.get("lldp") or {}
    device = info.get("deviceId") or info.get("systemName") or ""
    if not device:
        return ""
    return f"{device}:{info['portId']}" if info.get("portId") else device


def kbps_to_mbps(kbps: float | None) -> float:
    """Convert kilobits per second to megabits per second, rounded to 3 places.

    Example:
        >>> kbps_to_mbps(1536)
        1.536
    """
    return round((kbps or 0) / 1000, 3)


def port_row(port: dict[str, Any], *, switch: dict[str, Any], network: str, timestamp: str) -> dict[str, Any]:
    """Return one CSV row for a port status from ``getDeviceSwitchPortsStatuses``."""
    traffic = port.get("trafficInKbps") or {}
    return {
        "timestamp": timestamp,
        "network": network,
        "switch": switch.get("name") or switch["serial"],
        "serial": switch["serial"],
        "port": port["portId"],
        "enabled": port.get("enabled"),
        "status": port.get("status"),
        "speed": port.get("speed", ""),
        "duplex": port.get("duplex", ""),
        "recv_mbps": kbps_to_mbps(traffic.get("recv")),
        "sent_mbps": kbps_to_mbps(traffic.get("sent")),
        "total_mbps": kbps_to_mbps(traffic.get("total")),
        "usage_kb": (port.get("usageInKb") or {}).get("total", 0),
        "clients": port.get("clientCount", 0),
        "errors": len(port.get("errors") or []),
        "warnings": len(port.get("warnings") or []),
        "neighbour": neighbour_of(port),
    }


def hours_arg(value: str) -> int:
    """Argparse type for a look-back period between 1 hour and 31 days."""
    hours = int(value)
    if not 1 <= hours <= MAX_HOURS:
        raise argparse.ArgumentTypeError(f"--hours must be between 1 and {MAX_HOURS}")
    return hours


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__)
    parser.add_argument("--hours", type=hours_arg, default=24, help="look-back period (default: 24)")
    parser.add_argument(
        "--top", type=int, default=20, help="how many of the busiest ports to show (default: 20)"
    )
    parser.add_argument("--csv", action="store_true", help="save every port to a CSV file")
    add_switch_filters(parser)
    return parser


def run(context: ToolContext) -> int:
    """Collect port statuses from every matching switch and report on them."""
    dashboard, org_id, args, log = context.dashboard, context.organization_id, context.args, context.logger
    seconds = args.hours * 3600

    filters: dict[str, Any] = {}
    if args.switch:
        filters["name"] = args.switch
    if args.network:
        filters["networkIds"] = find_network_ids(dashboard, org_id, args.network)
        if not filters["networkIds"]:
            log.warning("No switch networks match %r", args.network)
            return 0

    networks = dashboard.organizations.getOrganizationNetworks(
        org_id, productTypes=["switch"], total_pages="all"
    )
    network_names = {n["id"]: n["name"] for n in networks}
    switches = dashboard.organizations.getOrganizationDevices(
        org_id, productTypes=["switch"], total_pages="all", **filters
    )

    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    rows: list[dict[str, Any]] = []
    failed = 0
    for switch in sorted(switches, key=lambda s: (s.get("name") or s["serial"]).lower()):
        name = switch.get("name") or switch["serial"]
        log.debug("Reading port statuses for %s", name)
        try:
            ports = dashboard.switch.getDeviceSwitchPortsStatuses(switch["serial"], timespan=seconds)
        except meraki.APIError as error:
            # Skip this switch rather than reusing the previous switch's ports.
            log.warning("Skipping %s: %s", name, format_api_error(error))
            failed += 1
            continue
        network = network_names.get(switch.get("networkId"), "(no network)")
        rows += [port_row(p, switch=switch, network=network, timestamp=timestamp) for p in ports]

    log.info("Collected %d ports from %d switches (%d skipped)", len(rows), len(switches) - failed, failed)
    busiest = sorted(rows, key=lambda r: r["total_mbps"], reverse=True)[: args.top]
    if busiest:
        print(f"\nTop {len(busiest)} busiest ports (average over {args.hours} h):")
        print(format_table(busiest, TOP_COLUMNS))
    if args.csv:
        path = write_csv(rows, COLUMNS, dated_output_path(TOOL_NAME, "port_status", ".csv"))
        log.info("Saved %s", path)
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
