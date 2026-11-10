"""Shared command-line plumbing for the tools.

Every tool follows the same shape::

    TOOL_NAME = "remove_stp"

    def build_parser() -> argparse.ArgumentParser:
        parser = base_parser(__doc__, changes_config=True)
        add_switch_filters(parser)
        return parser

    def run(context: ToolContext) -> int:
        ...  # the tool's actual work
        return 0

    def main(argv: Sequence[str] | None = None) -> int:
        return run_tool(TOOL_NAME, build_parser(), run, argv)

    if __name__ == "__main__":
        raise SystemExit(main())

That gives every tool the same options, logging, error handling and exit
codes, and keeps right-click → Run in PyCharm working.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import meraki

from meraki_tools.core.action_batch import ActionBatcher
from meraki_tools.core.client import MissingAPIKeyError, get_dashboard
from meraki_tools.core.errors import format_api_error
from meraki_tools.core.logging_setup import setup_logging
from meraki_tools.core.organizations import OrganizationSelectionError, get_organization_id
from meraki_tools.core.paths import log_dir

#: Exit code for success.
EXIT_OK = 0
#: Exit code when the Dashboard API returned an error.
EXIT_API_ERROR = 1
#: Exit code for a setup problem, such as a missing API key.
EXIT_CONFIG_ERROR = 2
#: Conventional exit code after Ctrl+C.
EXIT_INTERRUPTED = 130


@dataclass
class ToolContext:
    """Everything a tool's ``run`` function needs.

    Attributes:
        dashboard: Configured Dashboard API client.
        organization_id: The organisation to work on.
        args: Parsed command-line arguments.
        logger: Logger named after the tool.
    """

    dashboard: meraki.DashboardAPI
    organization_id: str
    args: argparse.Namespace
    logger: logging.Logger

    @property
    def dry_run(self) -> bool:
        """``True`` unless the tool changes configuration and ``--apply`` was given."""
        return not getattr(self.args, "apply", False)


def base_parser(description: str | None, *, changes_config: bool = False) -> argparse.ArgumentParser:
    """Return an argument parser with the options every tool shares.

    Args:
        description: Help text, usually the tool module's docstring.
        changes_config: Add ``--apply`` for tools that change configuration.
            Those tools only preview their changes unless ``--apply`` is given.

    Returns:
        A parser with ``--org-id`` and ``--verbose`` (and ``--apply`` if requested).
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--org-id",
        help="organisation ID; defaults to MERAKI_ORG_ID, or the only organisation the API key can see",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug messages")
    if changes_config:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="make the changes; without this flag the tool only logs what it would change",
        )
    return parser


def add_switch_filters(parser: argparse.ArgumentParser) -> None:
    """Add ``--network`` and ``--switch`` options for narrowing which switches are used."""
    group = parser.add_argument_group("switch selection")
    group.add_argument(
        "--network",
        metavar="TEXT",
        help="only switches in networks whose name contains TEXT (case-insensitive)",
    )
    group.add_argument(
        "--switch",
        metavar="TEXT",
        help="only switches whose name contains TEXT",
    )


def vlan_id(value: str) -> int:
    """Argparse type for a VLAN ID between 1 and 4094."""
    try:
        vlan = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not 1 <= vlan <= 4094:
        raise argparse.ArgumentTypeError(f"VLAN ID must be between 1 and 4094, got {vlan}")
    return vlan


def finish_changes(context: ToolContext, batcher: ActionBatcher, what: str) -> int:
    """Log how many changes were made (or would be) and return the exit code.

    Args:
        context: The running tool's context.
        batcher: The batcher that the changes were queued on. It must already
            have been flushed, for example by leaving its ``with`` block.
        what: Plural noun for the things changed, for example ``"access ports"``.

    Returns:
        ``EXIT_OK``, or ``EXIT_API_ERROR`` if any batch failed.
    """
    if context.dry_run:
        context.logger.info(
            "%d %s would change. Run again with --apply to make the changes.", batcher.submitted, what
        )
        return EXIT_OK
    context.logger.info("%d %s updated, %d failed", batcher.submitted, what, batcher.failed)
    return EXIT_API_ERROR if batcher.failed else EXIT_OK


def run_tool(
    tool_name: str,
    parser: argparse.ArgumentParser,
    run: Callable[[ToolContext], int | None],
    argv: Sequence[str] | None = None,
) -> int:
    """Parse arguments, set up logging and the API client, then call ``run``.

    Expected failures (missing API key, ambiguous organisation, API errors)
    are logged as a single clear line instead of a traceback.

    Args:
        tool_name: Short name used for the logger and log file.
        parser: The tool's argument parser.
        run: The tool's main function. It may return an exit code; ``None``
            counts as success.
        argv: Arguments to parse. Defaults to ``sys.argv[1:]``.

    Returns:
        A process exit code (see the ``EXIT_*`` constants).
    """
    args = parser.parse_args(argv)
    logger = setup_logging(
        tool_name, level=logging.DEBUG if args.verbose else logging.INFO, log_dir=log_dir()
    )

    try:
        dashboard = get_dashboard()
        context = ToolContext(
            dashboard=dashboard,
            organization_id=get_organization_id(dashboard, args.org_id),
            args=args,
            logger=logger,
        )
        if hasattr(args, "apply") and not args.apply:
            logger.info("Dry run: no changes will be made. Add --apply to make them.")
        result = run(context)
    except (MissingAPIKeyError, OrganizationSelectionError) as error:
        logger.error("%s", error)
        return EXIT_CONFIG_ERROR
    except meraki.APIError as error:
        logger.error("%s", format_api_error(error))
        return EXIT_API_ERROR
    except KeyboardInterrupt:
        logger.warning("Interrupted")
        return EXIT_INTERRUPTED

    return EXIT_OK if result is None else result
