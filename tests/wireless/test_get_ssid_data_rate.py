import pytest

from meraki_tools.wireless import get_ssid_data_rate as tool

HISTORY = [
    {"startTs": "t1", "endTs": "t2", "averageKbps": 2000, "downloadKbps": 2500, "uploadKbps": 1500},
    {"startTs": "t2", "endTs": "t3", "averageKbps": 4000, "downloadKbps": 4500, "uploadKbps": 3500},
    {"startTs": "t3", "endTs": "t4", "averageKbps": None, "downloadKbps": None, "uploadKbps": None},
]


def test_summarise_ignores_empty_intervals():
    assert tool.summarise(HISTORY) == {"intervals": 2, "avg_mbps": 3.0, "peak_mbps": 4.0, "peak_at": "t2"}


def test_summarise_no_data():
    assert tool.summarise([])["intervals"] == 0


@pytest.fixture
def wireless(dashboard):
    dashboard.organizations.getOrganizationNetworks.return_value = [{"id": "N_1", "name": "Main Campus"}]
    dashboard.wireless.getNetworkWirelessSsids.return_value = [
        {"number": 0, "name": "Staff WiFi", "enabled": True},
        {"number": 1, "name": "Staff Old", "enabled": False},
        {"number": 2, "name": "Guest", "enabled": True},
    ]
    dashboard.wireless.getNetworkWirelessDataRateHistory.return_value = HISTORY
    return dashboard


def test_only_enabled_matching_ssids_are_queried(wireless, capsys):
    assert tool.main(["staff", "--hours", "2", "--resolution", "600"]) == 0

    (call,) = wireless.wireless.getNetworkWirelessDataRateHistory.call_args_list
    assert call.kwargs == {"timespan": 7200, "resolution": 600, "ssid": 0}
    assert "Staff WiFi" in capsys.readouterr().out


def test_csv_has_one_row_per_interval(wireless, isolated_env):
    tool.main(["Staff", "--csv"])
    (csv_file,) = (isolated_env / "output" / "get_ssid_data_rate").glob("*.csv")
    assert len(csv_file.read_text().splitlines()) == 1 + len(HISTORY)


def test_invalid_resolution_rejected():
    with pytest.raises(SystemExit):
        tool.main(["Staff", "--resolution", "60"])


def test_no_match_is_not_an_error(wireless):
    assert tool.main(["nothing-like-this"]) == 0
