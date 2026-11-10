"""Add a tag to trunk ports so they are easy to find and filter in the Dashboard.

Ports that already have the tag are skipped, and existing tags are kept.

Examples:
    Preview tagging every trunk port with "Trunk":

        meraki-tools tag-trunk-ports

    Tag only switch-to-switch uplinks (native VLAN 1001) with "Uplink":

        meraki-tools tag-trunk-ports --tag Uplink --native-vlan 1001 --apply
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

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

TOOL_NAME = "tag_all_trunk_ports"


def tags_after_change(port: Port, tag: str, native_vlan: int | None = None) -> list[str] | None:
    """Return the port's new tag list, or ``None`` if it should not change.

    Args:
        port: Port configuration from the Dashboard API.
        tag: Tag to add.
        native_vlan: Only change trunks with this native VLAN. ``None`` means any trunk.

    Returns:
        The existing tags plus ``tag``, or ``None`` if the port is not a
        matching trunk or already has the tag.
    """
    if port.get("type") != "trunk":
        return None
    if native_vlan is not None and port.get("vlan") != native_vlan:
        return None
    tags = list(port.get("tags") or [])
    if tag in tags:
        return None
    return [*tags, tag]


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__, changes_config=True)
    parser.add_argument("--tag", default="Trunk", help="tag to add (default: %(default)s)")
    parser.add_argument(
        "--native-vlan",
        type=vlan_id,
        metavar="VLAN",
        help="only tag trunks with this native VLAN (default: every trunk)",
    )
    add_switch_filters(parser)
    return parser


def run(context: ToolContext) -> int:
    """Queue a tag update for every matching trunk port."""
    args, log = context.args, context.logger

    with ActionBatcher(context.dashboard, context.organization_id, dry_run=context.dry_run) as batcher:
        for switch, ports in iter_switch_ports(
            context.dashboard, context.organization_id, network=args.network, switch_name=args.switch
        ):
            for port in ports:
                new_tags = tags_after_change(port, args.tag, args.native_vlan)
                if new_tags is None:
                    continue
                log.info("%s port %s: add tag %r", switch.name, port["portId"], args.tag)
                batcher.update(port_resource(switch.serial, port["portId"]), {"tags": new_tags})

    return finish_changes(context, batcher, "trunk ports")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
