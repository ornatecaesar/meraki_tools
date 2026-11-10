from unittest.mock import MagicMock

import meraki

from meraki_tools.switching import export_subnet_info as tool


def _l2_error():
    response = MagicMock(status_code=400, reason="Bad Request")
    response.json.return_value = {"errors": ["not supported"]}
    return meraki.APIError({"tags": ["switch"], "operation": "getDeviceSwitchRoutingInterfaces"}, response)


def test_exports_stacks_and_standalone_switches(dashboard, isolated_env):
    dashboard.organizations.getOrganizationNetworks.return_value = [{"id": "N_1", "name": "Main Campus"}]
    dashboard.organizations.getOrganizationDevices.return_value = [
        {"serial": "Q-STACKED", "name": "Core 1", "networkId": "N_1"},
        {"serial": "Q-L3", "name": "Dist 1", "networkId": "N_1"},
        {"serial": "Q-L2", "name": "Edge 1", "networkId": "N_1"},
    ]
    dashboard.switch.getNetworkSwitchStacks.return_value = [
        {"id": "S_1", "name": "Core", "serials": ["Q-STACKED"]}
    ]
    dashboard.switch.getNetworkSwitchStackRoutingInterfaces.return_value = [
        {"name": "Staff", "vlanId": 10, "subnet": "10.0.10.0/24", "interfaceIp": "10.0.10.1"}
    ]

    def device_interfaces(serial):
        if serial == "Q-L2":
            raise _l2_error()
        return [{"name": "Guest", "vlanId": 20, "subnet": "10.0.20.0/24", "interfaceIp": "10.0.20.1"}]

    dashboard.switch.getDeviceSwitchRoutingInterfaces.side_effect = device_interfaces

    assert tool.main([]) == 0

    called = [c.args[0] for c in dashboard.switch.getDeviceSwitchRoutingInterfaces.call_args_list]
    assert "Q-STACKED" not in called
    (csv_file,) = (isolated_env / "output" / "export_subnet_info").glob("l3_interfaces_*.csv")
    lines = csv_file.read_text().splitlines()
    assert lines[1].startswith("Main Campus,Core,Staff,10")
    assert lines[2].startswith("Main Campus,Dist 1,Guest,20")
    assert len(lines) == 3
