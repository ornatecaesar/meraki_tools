"""Consistent logging for every tool.

Each tool calls :func:`setup_logging` once at start-up. Log records go to the
console and to ``logs/<tool name>.log``. The ``logs/`` folder is git-ignored
because log files can contain device names, serials and other network details.
"""

from __future__ import annotations

import logging
from pathlib import Path

#: Default folder for log files, relative to the current working directory.
DEFAULT_LOG_DIR = Path("logs")

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    tool_name: str,
    *,
    level: int = logging.INFO,
    log_dir: Path | str | None = DEFAULT_LOG_DIR,
    meraki_level: int = logging.WARNING,
) -> logging.Logger:
    """Configure the root logger and return a logger for the calling tool.

    Calling this more than once replaces the handlers from the previous call,
    so log lines are never duplicated.

    Args:
        tool_name: Short name of the tool, used for the logger and the log
            file name (for example ``"remove_stp"`` writes ``logs/remove_stp.log``).
        level: Minimum level for the tool's own messages.
        log_dir: Folder for the log file. It is created if needed. Pass
            ``None`` to log to the console only.
        meraki_level: Minimum level for messages from the ``meraki`` library,
            which logs every request at INFO and is very noisy below WARNING.

    Returns:
        The logger named after ``tool_name``.
    """
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_dir is not None:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path / f"{tool_name}.log", encoding="utf-8"))

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("meraki").setLevel(meraki_level)

    return logging.getLogger(tool_name)
