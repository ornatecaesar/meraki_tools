"""Build a PDF of peak port utilisation for each switch.

Each page is one switch: a bar per port showing the highest average
bandwidth (in Mbps) seen in any single interval over the look-back period.
It is a quick way to spot saturated uplinks and ports that are never used.

Note that each bar is the peak of *interval averages* (4 hours by default),
not an instantaneous peak. Use a shorter ``--interval`` for spikier detail.

Replaces the separate ``switch_port_utilization`` and
``stack_port_utilization`` scripts; use ``--stacks-only`` for the latter.

The PDF is written to
``output/port_utilization_report/port_utilization_<date>_<days>d.pdf``.

Examples:
    Every switch over the last 30 days:

        meraki-tools port-utilization-report

    Stack members in one network over the last week, in 20-minute intervals:

        meraki-tools port-utilization-report --days 7 --interval 1200 --stacks-only --network College
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from typing import Any

import matplotlib

# Render to files only (no window), so the report also runs without a display.
# The backend must be chosen before pyplot is imported.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from meraki_tools.core.cli import ToolContext, add_switch_filters, base_parser, run_tool
from meraki_tools.core.output import dated_output_path
from meraki_tools.core.switches import find_network_ids

TOOL_NAME = "port_utilization_report"

#: Interval lengths, in seconds, that the usage history endpoint accepts.
INTERVALS = (300, 1200, 14400, 86400)
#: Longest look-back the endpoint allows.
MAX_DAYS = 31


def peak_mbps_by_port(ports: list[dict[str, Any]]) -> dict[str, float]:
    """Return each port's highest interval-average bandwidth in Mbps.

    Args:
        ports: The ``ports`` list for one switch from
            ``getOrganizationSwitchPortsUsageHistoryByDeviceByInterval``.

    Returns:
        ``{port_id: peak_mbps}`` for every port that has at least one interval.

    Example:
        >>> peak_mbps_by_port([{"portId": "1", "intervals": [
        ...     {"bandwidth": {"usage": {"total": 1500.0}}},
        ...     {"bandwidth": {"usage": {"total": 500.0}}}]}])
        {'1': 1.5}
    """
    peaks: dict[str, float] = {}
    for port in ports:
        totals = [
            (interval.get("bandwidth") or {}).get("usage", {}).get("total") or 0.0
            for interval in port.get("intervals", [])
        ]
        if totals:
            peaks[port["portId"]] = max(totals) / 1000  # The API reports kbps.
    return peaks


def port_sort_key(port_id: str) -> tuple[int, int | str]:
    """Sort numeric port IDs numerically and anything else (module ports) after them."""
    return (0, int(port_id)) if port_id.isdigit() else (1, port_id)


def make_figure(switch_name: str, peaks: dict[str, float], days: int) -> plt.Figure:
    """Return a bar chart of peak utilisation for one switch."""
    port_ids = sorted(peaks, key=port_sort_key)
    values = [peaks[p] for p in port_ids]

    fig, ax = plt.subplots(figsize=(18, 6))
    bars = ax.bar(port_ids, values)
    ax.bar_label(bars, fmt="%.1f", fontsize=8)
    ax.set_title(f"Peak port utilisation (Mbps): {switch_name}\nLast {days} days to {date.today():%d-%m-%Y}")
    ax.set_xlabel("Port")
    ax.set_ylabel("Peak interval average (Mbps)")
    ax.margins(x=0.01)
    fig.tight_layout()
    return fig


def days_arg(value: str) -> int:
    """Argparse type for a look-back period of 1 to 31 days."""
    days = int(value)
    if not 1 <= days <= MAX_DAYS:
        raise argparse.ArgumentTypeError(f"--days must be between 1 and {MAX_DAYS}")
    return days


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__)
    parser.add_argument("--days", type=days_arg, default=30, help="look-back period in days (default: 30)")
    parser.add_argument(
        "--interval",
        type=int,
        choices=INTERVALS,
        default=14400,
        help="interval length in seconds (default: 14400, i.e. 4 hours)",
    )
    parser.add_argument(
        "--stacks-only", action="store_true", help="only include switches that are in a stack"
    )
    add_switch_filters(parser)
    return parser


def _stack_serials(context: ToolContext, network_ids: list[str] | None) -> set[str]:
    dashboard = context.dashboard
    if network_ids is None:
        networks = dashboard.organizations.getOrganizationNetworks(
            context.organization_id, productTypes=["switch"], total_pages="all"
        )
        network_ids = [n["id"] for n in networks]
    return {
        serial
        for network_id in network_ids
        for stack in dashboard.switch.getNetworkSwitchStacks(network_id)
        for serial in stack.get("serials", [])
    }


def run(context: ToolContext) -> int:
    """Fetch usage history, draw one page per switch and save the PDF."""
    dashboard, args, log = context.dashboard, context.args, context.logger

    filters: dict[str, Any] = {}
    network_ids = None
    if args.network:
        network_ids = find_network_ids(dashboard, context.organization_id, args.network)
        if not network_ids:
            log.warning("No switch networks match %r", args.network)
            return 0
        filters["networkIds"] = network_ids
    if args.switch:
        filters["name"] = args.switch
    if args.stacks_only:
        filters["serials"] = sorted(_stack_serials(context, network_ids))
        if not filters["serials"]:
            log.warning("No stacked switches found")
            return 0

    log.info("Fetching %d days of port usage in %d-second intervals", args.days, args.interval)
    switches = dashboard.switch.getOrganizationSwitchPortsUsageHistoryByDeviceByInterval(
        context.organization_id,
        timespan=args.days * 86400,
        interval=args.interval,
        total_pages="all",
        **filters,
    )
    # Older library versions return a bare list; newer ones wrap it as {"items": [...]}.
    items = switches.get("items", []) if isinstance(switches, dict) else switches

    path = dated_output_path(TOOL_NAME, "port_utilization", f"_{args.days}d.pdf")
    pages = 0
    with PdfPages(path) as pdf:
        for item in sorted(items, key=lambda i: (i.get("name") or i["serial"]).lower()):
            name = item.get("name") or item["serial"]
            peaks = peak_mbps_by_port(item.get("ports", []))
            if not peaks:
                log.info("No usage data for %s", name)
                continue
            fig = make_figure(name, peaks, args.days)
            pdf.savefig(fig, dpi=150)
            plt.close(fig)
            pages += 1

    if not pages:
        path.unlink(missing_ok=True)
        log.warning("No usage data returned, so no report was written")
        return 0
    log.info("Saved %d pages to %s", pages, path)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
