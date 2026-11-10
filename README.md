# Meraki Tools

[![CI](https://github.com/ornatecaesar/meraki_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/ornatecaesar/meraki_tools/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Command-line tools for automating and reporting on Cisco Meraki switch and
wireless networks, built on the official
[Meraki Dashboard API Python library](https://github.com/meraki/dashboard-api-python).

They grew out of day-to-day network administration: bulk port changes that
would take hours by hand in the Dashboard, audits of where a VLAN is carried,
utilisation reports for capacity planning, and configuration backups.

## Highlights

- **Safe by default.** Every tool that changes configuration only previews
  what it would change. Nothing is touched until you add `--apply`, and ports
  that are already correct are skipped, so re-running a tool is harmless.
- **Efficient.** Organisation-wide, paginated endpoints and
  [action batches](https://developer.cisco.com/meraki/api-v1/action-batches-overview/)
  replace one API call per switch or port, which keeps large runs fast and
  well inside the rate limit.
- **Consistent.** One shared core handles the API client, organisation
  selection, logging, output paths and error handling, so every tool has the
  same options and behaves the same way.
- **Tested.** Each tool is covered end-to-end against a fake Dashboard client,
  and CI runs [ruff](https://docs.astral.sh/ruff/) and pytest on Python 3.11 to 3.14.

## Tools

Run `meraki-tools` on its own to list them, or `meraki-tools <tool> --help` for
a tool's options and examples.

| Tool | What it does | Changes config |
|---|---|:---:|
| **Switching** | | |
| `remove-stp` | Disable RSTP and enable BPDU guard on access ports | ✔ |
| `tag-trunk-ports` | Add a tag to trunk ports, optionally only those with a given native VLAN | ✔ |
| `desk-port-to-wifi-trunk` | Turn tagged desk ports into PoE trunks for desk-mounted access points | ✔ |
| `find-ports-with-vlan` | List every port that carries a VLAN, and why (access, voice, native or allowed) | |
| `export-subnet-info` | Export every layer 3 interface on switches and stacks to CSV | |
| **Wireless** | | |
| `add-vlan-to-ap-trunks` | Add a VLAN to access point trunks and the uplinks that feed them | ✔ |
| `remove-vlan-from-ap-trunks` | Remove a VLAN from those trunks, splitting ranges where needed | ✔ |
| `ssid-data-rate` | Average and peak data rate per SSID over a period, with optional CSV | |
| **Reporting** | | |
| `port-utilization-report` | PDF with a peak-utilisation chart per switch (or per stack member) | |
| `port-status-snapshot` | Busiest ports with status, traffic, errors and CDP/LLDP neighbours | |
| **Backups** | | |
| `backup-l3-firewall-rules` | Save MX L3 firewall rules, policy objects and groups to JSON | |

## Getting started

### 1. Install

You need Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```shell
git clone https://github.com/ornatecaesar/meraki_tools.git
cd meraki_tools
uv sync
```

`uv sync` creates a `.venv` folder with the exact dependency versions from
`uv.lock` and installs the tools into it.

### 2. Provide an API key

Create a key in the Dashboard under **My profile → API access**. The tools
read it from the `MERAKI_API_KEY` environment variable, so it never needs to
appear in code or on the command line.

```shell
# macOS / Linux
export MERAKI_API_KEY="your-key"

# Windows PowerShell
$env:MERAKI_API_KEY = "your-key"
```

If your key can see more than one organisation, also set `MERAKI_ORG_ID`
or pass `--org-id`. The tools refuse to guess.

For the reporting and backup tools, a key from an account with read-only
access is enough.

### 3. Run a tool

```shell
uv run meraki-tools find-ports-with-vlan 100
uv run meraki-tools remove-stp --network "Main Campus"           # preview
uv run meraki-tools remove-stp --network "Main Campus" --apply   # make the changes
```

## Using PyCharm

1. Open the project folder. When PyCharm asks for an interpreter, choose
   **uv** (or point it at `.venv`).
2. Go to **Run → Edit Configurations → Edit configuration templates… → Python**
   and set:
   - **Working directory**: the project root.
   - **Environment variables**: `MERAKI_API_KEY=your-key`.
3. Right-click any tool under `src/meraki_tools/` and choose **Run**. Add
   options such as `--network College --apply` in the run configuration's
   **Parameters** box.

Every tool module works this way, as well as through `meraki-tools`.

## Options common to every tool

| Option | Meaning |
|---|---|
| `--org-id ID` | Organisation to use. Defaults to `MERAKI_ORG_ID`, or the only organisation the key can see. |
| `--network TEXT` | Only networks whose name contains `TEXT` (case-insensitive). |
| `--switch TEXT` | Only switches whose name contains `TEXT` (switch tools). |
| `--apply` | Make the changes (tools that change config). Without it, the tool only logs what it would do. |
| `-v`, `--verbose` | Show debug messages. |

## Output and logs

Logs go to `logs/<tool>.log` and files to `output/<tool>/`, both in the
project root, wherever the tool is started from. Set `MERAKI_TOOLS_HOME` to
use a different folder.

Both folders are git-ignored. Reports, exports and backups contain real
network details (device names, serials, subnets and firewall rules), so keep
them out of version control and store them somewhere access-controlled.

## Project layout

```
src/meraki_tools/
├── cli.py            # the meraki-tools command
├── core/             # shared building blocks
│   ├── client.py         # configured Dashboard API client
│   ├── cli.py            # common options, error handling, exit codes
│   ├── organizations.py  # safe organisation selection
│   ├── switches.py       # org-wide switch and port lookup
│   ├── action_batch.py   # batched changes with dry-run support
│   ├── vlans.py          # parse and edit allowedVlans strings
│   ├── output.py, paths.py, logging_setup.py, errors.py
├── switching/        # switch port tools
├── wireless/         # access point trunk and SSID tools
├── reporting/        # utilisation reports
└── backups/          # configuration backups
tests/                # pytest suite with a fake Dashboard client
```

## Development

```shell
uv run pytest             # tests, including doctests in the package
uv run ruff check .       # lint
uv run ruff format .      # format
```

To add a tool, create a module with `build_parser()`, `run(context)` and
`main(argv)` that calls `meraki_tools.core.cli.run_tool` (any existing tool is
a template), then register its command name in `src/meraki_tools/cli.py`.
Tests should use the `dashboard` fixture in `tests/conftest.py` with
synthetic data only.

## License

[MIT](LICENSE)
