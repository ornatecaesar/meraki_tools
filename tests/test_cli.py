import importlib

import pytest

from meraki_tools import cli
from meraki_tools.core import cli as core_cli
from meraki_tools.core.client import MissingAPIKeyError


def test_lists_tools(capsys):
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    for name in cli.COMMANDS:
        assert name in out


def test_unknown_tool(capsys):
    assert cli.main(["nope"]) == 2
    assert "unknown tool" in capsys.readouterr().err


def test_every_command_module_has_main():
    for module in cli.COMMANDS.values():
        assert callable(importlib.import_module(module).main)


def test_dispatches_to_tool(dashboard):
    assert cli.main(["remove-stp"]) == 0
    dashboard.switch.getOrganizationSwitchPortsBySwitch.assert_called_once()


def test_missing_api_key_is_a_clean_error(monkeypatch):
    def no_key():
        raise MissingAPIKeyError("no key")

    monkeypatch.setattr("meraki_tools.core.cli.get_dashboard", no_key)
    assert cli.main(["remove-stp"]) == core_cli.EXIT_CONFIG_ERROR


def test_several_orgs_is_a_clean_error(dashboard):
    dashboard.organizations.getOrganizations.return_value = [
        {"id": "1", "name": "A"},
        {"id": "2", "name": "B"},
    ]
    assert cli.main(["remove-stp"]) == core_cli.EXIT_CONFIG_ERROR


def test_vlan_id_type():
    assert core_cli.vlan_id("16") == 16
    with pytest.raises(Exception, match="between 1 and 4094"):
        core_cli.vlan_id("5000")
