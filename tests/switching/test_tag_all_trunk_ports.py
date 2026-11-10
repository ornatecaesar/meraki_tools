from meraki_tools.switching import tag_all_trunk_ports as tool
from tests.conftest import make_port, make_switch, sent_actions


def test_tags_after_change():
    trunk = make_port(1, type="trunk", vlan=1001, tags=["Existing"])
    assert tool.tags_after_change(trunk, "Trunk") == ["Existing", "Trunk"]
    assert tool.tags_after_change(trunk, "Existing") is None
    assert tool.tags_after_change(trunk, "Trunk", native_vlan=16) is None
    assert tool.tags_after_change(make_port(2), "Trunk") is None


def test_original_tags_are_not_mutated():
    port = make_port(1, type="trunk", tags=["A"])
    tool.tags_after_change(port, "B")
    assert port["tags"] == ["A"]


def test_apply_tags_every_untagged_trunk(dashboard):
    ports = [
        make_port(1, type="trunk"),
        make_port(2, type="trunk", tags=["Trunk"]),
        make_port(3),
    ]
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [
        make_switch("SW1", "Q-1", ports),
        make_switch("SW2", "Q-2", [make_port(9, type="trunk")]),
    ]

    assert tool.main(["--apply"]) == 0
    assert [a["resource"] for a in sent_actions(dashboard)] == [
        "/devices/Q-1/switch/ports/1",
        "/devices/Q-2/switch/ports/9",
    ]
