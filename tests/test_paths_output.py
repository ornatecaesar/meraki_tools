from pathlib import Path

from meraki_tools.core import paths
from meraki_tools.core.output import format_table, write_csv


def test_home_override(isolated_env):
    assert paths.base_dir() == isolated_env
    assert paths.output_dir("demo") == isolated_env / "output" / "demo"
    assert (isolated_env / "output" / "demo").is_dir()


def test_repo_root_used_without_override(monkeypatch):
    monkeypatch.delenv("MERAKI_TOOLS_HOME")
    assert (paths.base_dir() / "pyproject.toml").is_file()


def test_write_csv_ignores_extra_keys(tmp_path: Path):
    path = write_csv([{"a": 1, "extra": 2}], ["a"], tmp_path / "sub" / "x.csv")
    assert path.read_text().splitlines() == ["a", "1"]


def test_format_table_blank_for_none():
    assert format_table([{"a": None}], ["a"]) == "a\n-\n"
