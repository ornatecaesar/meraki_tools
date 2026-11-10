"""Disable RSTP and enable BPDU guard on access ports.

Access ports should only ever connect to end devices, so running spanning
tree on them only slows down link-up. BPDU guard then shuts a port down if a
switch is plugged into it, which protects the network from accidental loops.

Ports that are already set this way are skipped, so the tool is safe to run
repeatedly.

Examples:
    Preview the changes for every switch in the organisation:

        meraki-tools remove-stp

    Apply them to switches in networks whose name contains "College":

        meraki-tools remove-stp --network College --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from meraki_tools.core import ActionBatcher
from meraki_tools.core.cli import ToolContext, add_switch_filters, base_parser, finish_changes, run_tool
from meraki_tools.core.switches import Port, iter_switch_ports, port_resource

TOOL_NAME = "remove_stp"

#: Port settings this tool enforces on access ports.
TARGET_SETTINGS = {"rstpEnabled": False, "stpGuard": "bpdu guard"}


def needs_change(port: Port) -> bool:
    """Return whether an access port still needs RSTP disabling or BPDU guard.

    Args:
        port: Port configuration from the Dashboard API.

    Returns:
        ``True`` for access ports whose settings differ from :data:`TARGET_SETTINGS`.
    """
    if port.get("type") != "access":
        return False
    return any(port.get(key) != value for key, value in TARGET_SETTINGS.items())


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__, changes_config=True)
    add_switch_filters(parser)
    return parser


def run(context: ToolContext) -> int:
    """Queue an update for every access port that needs it."""
    args, log = context.args, context.logger

    with ActionBatcher(context.dashboard, context.organization_id, dry_run=context.dry_run) as batcher:
        for switch, ports in iter_switch_ports(
            context.dashboard, context.organization_id, network=args.network, switch_name=args.switch
        ):
            for port in filter(needs_change, ports):
                log.info("%s port %s: disable RSTP, enable BPDU guard", switch.name, port["portId"])
                batcher.update(port_resource(switch.serial, port["portId"]), dict(TARGET_SETTINGS))

    return finish_changes(context, batcher, "access ports")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
