"""Shared fixtures: a fake Dashboard client and an isolated output folder.

The fake returns synthetic data only. No real network details belong in tests.
"""

from unittest.mock import MagicMock

import pytest


def make_port(port_id, **settings):
    port = {
        "portId": str(port_id),
        "name": None,
        "tags": [],
        "enabled": True,
        "poeEnabled": True,
        "type": "access",
        "vlan": 1,
        "voiceVlan": None,
        "allowedVlans": "all",
        "rstpEnabled": True,
        "stpGuard": "disabled",
    }
    port.update(settings)
    return port


def make_switch(name, serial, ports, network=("N_1", "Main Campus")):
    return {
        "name": name,
        "serial": serial,
        "model": "MS120-8FP",
        "network": {"id": network[0], "name": network[1]},
        "ports": ports,
    }


@pytest.fixture
def dashboard():
    mock = MagicMock()
    mock.organizations.getOrganizations.return_value = [{"id": "O_1", "name": "Example Org"}]
    mock.organizations.getOrganizationNetworks.return_value = [
        {"id": "N_1", "name": "Main Campus"},
        {"id": "N_2", "name": "Annex"},
    ]
    mock.switch.getOrganizationSwitchPortsBySwitch.return_value = []
    mock.organizations.createOrganizationActionBatch.return_value = {
        "id": "B_1",
        "status": {"failed": False, "errors": []},
    }
    return mock


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path, dashboard):
    """Point output at a temp folder and make every tool use the fake client."""
    monkeypatch.setenv("MERAKI_TOOLS_HOME", str(tmp_path))
    monkeypatch.setenv("MERAKI_API_KEY", "0" * 40)
    monkeypatch.delenv("MERAKI_ORG_ID", raising=False)
    monkeypatch.setattr("meraki_tools.core.cli.get_dashboard", lambda: dashboard)
    return tmp_path


def sent_actions(dashboard):
    """Return every action sent in any action batch."""
    return [
        action
        for call in dashboard.organizations.createOrganizationActionBatch.call_args_list
        for action in call.kwargs["actions"]
    ]
