"""Where tools write their logs and output files.

Output always lands in the same place, however a tool is started (PyCharm's
right-click Run, ``python -m``, or the ``meraki-tools`` command), so files
never end up scattered inside the source tree.

The base folder is chosen in this order:

1. The ``MERAKI_TOOLS_HOME`` environment variable, if set.
2. The repository root, when running from a source checkout (including the
   editable install that ``uv sync`` creates).
3. The current working directory.

Under it, logs go to ``logs/`` and everything else to ``output/<tool name>/``.
Both folders are git-ignored because they can contain network details.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Environment variable that overrides the base folder for logs and output.
HOME_ENV_VAR = "MERAKI_TOOLS_HOME"


def base_dir() -> Path:
    """Return the folder that holds ``logs/`` and ``output/``."""
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser()

    # src/meraki_tools/core/paths.py -> repository root is three levels up.
    repo_root = Path(__file__).resolve().parents[3]
    if (repo_root / "pyproject.toml").is_file():
        return repo_root

    return Path.cwd()


def log_dir() -> Path:
    """Return the folder for log files (not created until something logs)."""
    return base_dir() / "logs"


def output_dir(tool_name: str) -> Path:
    """Return the output folder for one tool, creating it if needed.

    Args:
        tool_name: The tool's short name, for example ``"export_subnet_info"``.

    Returns:
        ``<base>/output/<tool_name>/``.
    """
    path = base_dir() / "output" / tool_name
    path.mkdir(parents=True, exist_ok=True)
    return path
