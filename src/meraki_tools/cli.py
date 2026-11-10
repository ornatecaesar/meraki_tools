"""The ``meraki-tools`` command: one entry point for every tool.

Usage::

    meraki-tools                  # list the available tools
    meraki-tools <tool> --help    # options for one tool
    meraki-tools <tool> [options]

Each tool can also be run on its own, either with right-click → Run in
PyCharm or with ``python -m meraki_tools.<area>.<module>``.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence

#: Command name → module that provides ``main(argv)``.
COMMANDS: dict[str, str] = {
    "add-vlan-to-ap-trunks": "meraki_tools.wireless.add_vlan_to_wifi_port",
    "backup-l3-firewall-rules": "meraki_tools.backups.backup_l3_firewall_rules",
    "desk-port-to-wifi-trunk": "meraki_tools.switching.set_desk_port_to_wifi_trunk",
    "export-subnet-info": "meraki_tools.switching.export_subnet_info",
    "find-ports-with-vlan": "meraki_tools.switching.find_ports_with_vlan",
    "port-status-snapshot": "meraki_tools.reporting.port_status_snapshot",
    "port-utilization-report": "meraki_tools.reporting.port_utilization_report",
    "remove-stp": "meraki_tools.switching.remove_stp",
    "remove-vlan-from-ap-trunks": "meraki_tools.wireless.remove_vlan_from_wifi_port",
    "ssid-data-rate": "meraki_tools.wireless.get_ssid_data_rate",
    "tag-trunk-ports": "meraki_tools.switching.tag_all_trunk_ports",
}


def _summary(module_name: str) -> str:
    """Return the first line of a tool module's docstring."""
    doc = importlib.import_module(module_name).__doc__ or ""
    return doc.strip().splitlines()[0] if doc.strip() else ""


def usage() -> str:
    """Return the list of available tools with a one-line summary of each."""
    width = max(len(name) for name in COMMANDS)
    lines = ["usage: meraki-tools <tool> [options]", "", "tools:"]
    lines += [f"  {name.ljust(width)}  {_summary(module)}" for name, module in sorted(COMMANDS.items())]
    lines += ["", "Run 'meraki-tools <tool> --help' for a tool's options."]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to the named tool.

    Args:
        argv: Command-line arguments without the program name. Defaults to
            ``sys.argv[1:]``.

    Returns:
        The tool's exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(usage())
        return 0

    command, *rest = args
    module_name = COMMANDS.get(command)
    if module_name is None:
        print(f"meraki-tools: unknown tool {command!r}\n\n{usage()}", file=sys.stderr)
        return 2

    tool = importlib.import_module(module_name)
    # Make the tool's --help and error messages show "meraki-tools <tool>".
    sys.argv[0] = f"meraki-tools {command}"
    return tool.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
