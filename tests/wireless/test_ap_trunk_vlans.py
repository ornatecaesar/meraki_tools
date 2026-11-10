import pytest

from meraki_tools.wireless import add_vlan_to_wifi_port as add_tool
from meraki_tools.wireless import remove_vlan_from_wifi_port as remove_tool
from meraki_tools.wireless.ap_trunks import is_ap_trunk
from tests.conftest import make_port, make_switch, sent_actions

AP_PORT = make_port(1, type="trunk", vlan=16, allowedVlans="16,35,40-50")
UPLINK = make_port(2, type="trunk", vlan=1001, allowedVlans="16,35,40-50,1001")
UPLINK_WITHOUT_AP_VLAN = make_port(3, type="trunk", vlan=1001, allowedVlans="35,1001")
ALL_TRUNK = make_port(4, type="trunk", vlan=16, allowedVlans="all")
ACCESS = make_port(5, vlan=16)


@pytest.mark.parametrize(
    ("port", "uplink_native", "expected"),
    [
        (AP_PORT, None, True),
        (UPLINK, None, False),
        (UPLINK, 1001, True),
        (UPLINK_WITHOUT_AP_VLAN, 1001, False),
        (ALL_TRUNK, 1001, False),
        (ACCESS, 1001, False),
    ],
)
def test_is_ap_trunk(port, uplink_native, expected):
    assert is_ap_trunk(port, 16, uplink_native) is expected


@pytest.fixture
def switch_ports(dashboard):
    ports = [AP_PORT, UPLINK, UPLINK_WITHOUT_AP_VLAN, ALL_TRUNK, ACCESS]
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [make_switch("SW1", "Q-1", ports)]


def _bodies(dashboard):
    return {a["resource"].rsplit("/", 1)[-1]: a["body"]["allowedVlans"] for a in sent_actions(dashboard)}


@pytest.mark.usefixtures("switch_ports")
def test_add_vlan_to_ap_ports_and_uplinks(dashboard):
    assert add_tool.main(["790", "--ap-vlan", "16", "--uplink-native-vlan", "1001", "--apply"]) == 0
    assert _bodies(dashboard) == {"1": "16,35,40-50,790", "2": "16,35,40-50,790,1001"}


@pytest.mark.usefixtures("switch_ports")
def test_add_skips_ports_that_already_have_it(dashboard):
    add_tool.main(["35", "--ap-vlan", "16", "--uplink-native-vlan", "1001", "--apply"])
    dashboard.organizations.createOrganizationActionBatch.assert_not_called()


@pytest.mark.usefixtures("switch_ports")
def test_add_dry_run_sends_nothing(dashboard):
    assert add_tool.main(["790", "--ap-vlan", "16"]) == 0
    dashboard.organizations.createOrganizationActionBatch.assert_not_called()


@pytest.mark.usefixtures("switch_ports")
def test_remove_vlan_splits_ranges(dashboard):
    assert remove_tool.main(["45", "--ap-vlan", "16", "--apply"]) == 0
    assert _bodies(dashboard) == {"1": "16,35,40-44,46-50"}


@pytest.mark.usefixtures("switch_ports")
def test_remove_refuses_the_management_vlan(dashboard):
    assert remove_tool.main(["16", "--ap-vlan", "16", "--apply"]) == 2
    dashboard.organizations.createOrganizationActionBatch.assert_not_called()
