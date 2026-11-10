from unittest.mock import MagicMock

import meraki

from meraki_tools.reporting import port_status_snapshot as tool


def _status(port_id, kbps, **extra):
    status = {
        "portId": str(port_id),
        "enabled": True,
        "status": "Connected",
        "speed": "1 Gbps",
        "duplex": "full",
        "errors": [],
        "warnings": [],
        "usageInKb": {"total": kbps * 10},
        "trafficInKbps": {"total": kbps, "sent": kbps / 2, "recv": kbps / 2},
        "clientCount": 1,
    }
    status.update(extra)
    return status


def test_neighbour_prefers_cdp():
    port = {"cdp": {"deviceId": "abc", "portId": "Port 1"}, "lldp": {"systemName": "x"}}
    assert tool.neighbour_of(port) == "abc:Port 1"
    assert tool.neighbour_of({}) == ""


def test_busiest_ports_printed_and_csv_saved(dashboard, isolated_env, capsys):
    dashboard.organizations.getOrganizationDevices.return_value = [
        {"serial": "Q-1", "name": "SW1", "networkId": "N_1"},
        {"serial": "Q-2", "name": "SW2", "networkId": "N_2"},
    ]
    dashboard.switch.getDeviceSwitchPortsStatuses.side_effect = lambda serial, timespan: (
        [_status(1, 5000), _status(2, 10)] if serial == "Q-1" else [_status(1, 900_000)]
    )

    assert tool.main(["--top", "2", "--csv"]) == 0

    out = capsys.readouterr().out
    assert out.index("SW2") < out.index("SW1")  # busiest first
    (csv_file,) = (isolated_env / "output" / "port_status_snapshot").glob("*.csv")
    lines = csv_file.read_text().splitlines()
    assert len(lines) == 4
    assert any(",Annex,SW2,Q-2,1," in line for line in lines[1:])


def test_api_error_skips_switch_without_reusing_ports(dashboard, isolated_env):
    response = MagicMock(status_code=500, reason="Server Error")
    response.json.return_value = None
    error = meraki.APIError({"tags": ["switch"], "operation": "getDeviceSwitchPortsStatuses"}, response)

    dashboard.organizations.getOrganizationDevices.return_value = [
        {"serial": "Q-1", "name": "SW1", "networkId": "N_1"},
        {"serial": "Q-2", "name": "SW2", "networkId": "N_1"},
    ]

    def statuses(serial, timespan):
        if serial == "Q-2":
            raise error
        return [_status(1, 100)]

    dashboard.switch.getDeviceSwitchPortsStatuses.side_effect = statuses

    assert tool.main(["--csv"]) == 1
    (csv_file,) = (isolated_env / "output" / "port_status_snapshot").glob("*.csv")
    rows = csv_file.read_text().splitlines()[1:]
    assert len(rows) == 1
    assert "SW2" not in rows[0]
