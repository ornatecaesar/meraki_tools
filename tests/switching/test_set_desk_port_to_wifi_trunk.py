import pytest

from meraki_tools.switching import set_desk_port_to_wifi_trunk as tool
from tests.conftest import make_port, make_switch, sent_actions

ARGS = ["--port-tag", "DESK", "--native-vlan", "16", "--allowed-vlans", "16, 150, 700-701"]


def test_needs_change_compares_vlan_sets():
    settings = tool.trunk_settings(16, "16,150,700,701")
    done = make_port(1, type="trunk", vlan=16, allowedVlans="16,150,700-701")
    assert not tool.needs_change(done, settings)
    assert tool.needs_change(make_port(2), settings)


def test_allowed_vlans_are_normalised():
    assert tool.allowed_vlans_arg("16, 150, 700,701,702") == "16,150,700-702"


def test_bad_allowed_vlans_rejected():
    with pytest.raises(SystemExit):
        tool.main(["--port-tag", "DESK", "--native-vlan", "16", "--allowed-vlans", "abc"])


def test_apply_changes_tagged_ports_only(dashboard):
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [
        make_switch("SW1", "Q-1", [make_port(1, tags=["DESK"]), make_port(2)]),
    ]

    assert tool.main([*ARGS, "--apply"]) == 0
    (action,) = sent_actions(dashboard)
    assert action["resource"] == "/devices/Q-1/switch/ports/1"
    assert action["body"] == {
        "enabled": True,
        "poeEnabled": True,
        "type": "trunk",
        "vlan": 16,
        "allowedVlans": "16,150,700,701",
    }


def test_switch_tag_limits_switches(dashboard):
    dashboard.organizations.getOrganizationDevices.return_value = [{"serial": "Q-2"}]
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [
        make_switch("SW1", "Q-1", [make_port(1, tags=["DESK"])]),
        make_switch("SW2", "Q-2", [make_port(1, tags=["DESK"])]),
    ]

    tool.main([*ARGS, "--switch-tag", "IT", "--apply"])
    assert [a["resource"] for a in sent_actions(dashboard)] == ["/devices/Q-2/switch/ports/1"]
