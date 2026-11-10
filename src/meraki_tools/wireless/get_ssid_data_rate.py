"""Report the data rate history of an SSID across your wireless networks.

For each enabled SSID whose name contains the given text, fetches the average,
download and upload rates per interval over the chosen period, then prints a
summary (average and peak) and optionally saves every interval to CSV.

Examples:
    Last 24 hours in 5-minute intervals:

        meraki-tools ssid-data-rate "Staff WiFi"

    Last 7 days in hourly intervals, saved to output/get_ssid_data_rate/:

        meraki-tools ssid-data-rate Staff --hours 168 --resolution 3600 --csv
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from meraki_tools.core.cli import ToolContext, base_parser, run_tool
from meraki_tools.core.output import dated_output_path, format_table, write_csv

TOOL_NAME = "get_ssid_data_rate"

#: Interval lengths, in seconds, that the data rate history endpoint accepts.
RESOLUTIONS = (300, 600, 1200, 3600, 14400, 86400)
#: Longest period the endpoint can look back over (31 days).
MAX_HOURS = 31 * 24

CSV_COLUMNS = ["network", "ssid", "startTs", "endTs", "averageKbps", "downloadKbps", "uploadKbps"]
SUMMARY_COLUMNS = ["network", "ssid", "intervals", "avg_mbps", "peak_mbps", "peak_at"]


def summarise(intervals: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the interval count, mean and peak average rate (in Mbps).

    Intervals with no data (``averageKbps`` of ``None``) are ignored.

    Example:
        >>> summarise([{"startTs": "t1", "averageKbps": 1000}, {"startTs": "t2", "averageKbps": 3000}])
        {'intervals': 2, 'avg_mbps': 2.0, 'peak_mbps': 3.0, 'peak_at': 't2'}
    """
    with_data = [i for i in intervals if i.get("averageKbps") is not None]
    if not with_data:
        return {"intervals": 0, "avg_mbps": None, "peak_mbps": None, "peak_at": None}
    peak = max(with_data, key=lambda i: i["averageKbps"])
    mean = sum(i["averageKbps"] for i in with_data) / len(with_data)
    return {
        "intervals": len(with_data),
        "avg_mbps": round(mean / 1000, 1),
        "peak_mbps": round(peak["averageKbps"] / 1000, 1),
        "peak_at": peak.get("startTs"),
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
    parser.add_argument("ssid", help="include SSIDs whose name contains this text (case-insensitive)")
    parser.add_argument("--hours", type=hours_arg, default=24, help="how far back to look (default: 24)")
    parser.add_argument(
        "--resolution",
        type=int,
        choices=RESOLUTIONS,
        default=300,
        help="interval length in seconds (default: 300)",
    )
    parser.add_argument(
        "--network",
        metavar="TEXT",
        help="only networks whose name contains TEXT (case-insensitive)",
    )
    parser.add_argument("--csv", action="store_true", help="save every interval to a CSV file")
    return parser


def run(context: ToolContext) -> int:
    """Fetch and summarise the data rate history for every matching SSID."""
    dashboard, args, log = context.dashboard, context.args, context.logger

    networks = dashboard.organizations.getOrganizationNetworks(
        context.organization_id, productTypes=["wireless"], total_pages="all"
    )
    if args.network:
        networks = [n for n in networks if args.network.lower() in n["name"].lower()]

    needle = args.ssid.lower()
    summaries: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    for network in sorted(networks, key=lambda n: n["name"].lower()):
        for ssid in dashboard.wireless.getNetworkWirelessSsids(network["id"]):
            if not ssid.get("enabled") or needle not in ssid["name"].lower():
                continue
            intervals = dashboard.wireless.getNetworkWirelessDataRateHistory(
                network["id"], timespan=args.hours * 3600, resolution=args.resolution, ssid=ssid["number"]
            )
            labels = {"network": network["name"], "ssid": ssid["name"]}
            summaries.append({**labels, **summarise(intervals)})
            csv_rows += [{**labels, **interval} for interval in intervals]

    if not summaries:
        log.warning("No enabled SSID matching %r found", args.ssid)
        return 0

    print(format_table(summaries, SUMMARY_COLUMNS))
    if args.csv:
        path = write_csv(csv_rows, CSV_COLUMNS, dated_output_path(TOOL_NAME, "ssid_data_rate", ".csv"))
        log.info("Saved %d intervals to %s", len(csv_rows), path)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
