"""Back up MX security appliance layer 3 firewall rules to JSON.

Saves the L3 outbound rules of every network that has a security appliance,
plus the organisation's policy objects and policy object groups that those
rules can refer to, so a rule set can be read or restored later.

Files are written to a dated folder::

    output/backup_l3_firewall_rules/<date>/
        <network name>_l3_firewall_rules.json
        policy_objects.json
        policy_object_groups.json

Firewall rules describe how your network is protected, so these files are
git-ignored and should be stored somewhere access-controlled.

Example:
    meraki-tools backup-l3-firewall-rules --network "Head Office"
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from meraki_tools.core.cli import ToolContext, base_parser, run_tool
from meraki_tools.core.paths import output_dir

TOOL_NAME = "backup_l3_firewall_rules"


def safe_filename(name: str) -> str:
    """Return a network name made safe for use in a file name.

    Example:
        >>> safe_filename("Head Office / DMZ")
        'Head_Office_DMZ'
    """
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "network"


def write_json(data: Any, path: Path) -> Path:
    """Write data as indented JSON and return the path."""
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for this tool."""
    parser = base_parser(__doc__)
    parser.add_argument(
        "--network",
        metavar="TEXT",
        help="only networks whose name contains TEXT (case-insensitive)",
    )
    return parser


def run(context: ToolContext) -> int:
    """Export the rules of every matching appliance network and the policy objects."""
    dashboard, org_id, args, log = context.dashboard, context.organization_id, context.args, context.logger

    networks = dashboard.organizations.getOrganizationNetworks(
        org_id, productTypes=["appliance"], total_pages="all"
    )
    if args.network:
        networks = [n for n in networks if args.network.lower() in n["name"].lower()]
    if not networks:
        log.warning("No networks with a security appliance found, so there is nothing to back up")
        return 0

    folder = output_dir(TOOL_NAME) / date.today().isoformat()
    folder.mkdir(parents=True, exist_ok=True)

    for network in sorted(networks, key=lambda n: n["name"].lower()):
        rules = dashboard.appliance.getNetworkApplianceFirewallL3FirewallRules(network["id"])
        path = write_json(
            {"network": {"id": network["id"], "name": network["name"]}, **rules},
            folder / f"{safe_filename(network['name'])}_l3_firewall_rules.json",
        )
        log.info("%s: %d rules saved to %s", network["name"], len(rules.get("rules", [])), path.name)

    objects = dashboard.organizations.getOrganizationPolicyObjects(org_id, total_pages="all")
    groups = dashboard.organizations.getOrganizationPolicyObjectsGroups(org_id, total_pages="all")
    write_json(objects, folder / "policy_objects.json")
    write_json(groups, folder / "policy_object_groups.json")
    log.info("Saved %d policy objects and %d groups", len(objects), len(groups))
    log.info("Backup written to %s", folder)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool from the command line."""
    return run_tool(TOOL_NAME, build_parser(), run, argv)


if __name__ == "__main__":
    raise SystemExit(main())
