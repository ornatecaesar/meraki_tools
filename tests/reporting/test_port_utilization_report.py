import pytest

from meraki_tools.reporting import port_utilization_report as tool


def _interval(kbps):
    return {"bandwidth": {"usage": {"total": kbps}}}


def _history():
    return {
        "items": [
            {
                "name": "SW-B",
                "serial": "Q-2",
                "ports": [{"portId": "1", "intervals": [_interval(100.0)]}],
            },
            {
                "name": "SW-A",
                "serial": "Q-1",
                "ports": [
                    {"portId": "10", "intervals": [_interval(2000.0), _interval(500.0)]},
                    {"portId": "2", "intervals": [_interval(None)]},
                ],
            },
            {"name": "SW-EMPTY", "serial": "Q-3", "ports": [{"portId": "1", "intervals": []}]},
        ]
    }


def test_peak_mbps_by_port():
    ports = _history()["items"][1]["ports"]
    assert tool.peak_mbps_by_port(ports) == {"10": 2.0, "2": 0.0}


def test_port_sort_key_numeric_then_text():
    assert sorted(["10", "2", "1_MOD", "1"], key=tool.port_sort_key) == ["1", "2", "10", "1_MOD"]


def test_writes_one_page_per_switch_with_data(dashboard, isolated_env):
    dashboard.switch.getOrganizationSwitchPortsUsageHistoryByDeviceByInterval.return_value = _history()

    assert tool.main(["--days", "7", "--interval", "1200"]) == 0

    kwargs = dashboard.switch.getOrganizationSwitchPortsUsageHistoryByDeviceByInterval.call_args.kwargs
    assert kwargs["timespan"] == 7 * 86400
    assert kwargs["interval"] == 1200
    (pdf,) = (isolated_env / "output" / "port_utilization_report").glob("*_7d.pdf")
    content = pdf.read_bytes()
    assert content.startswith(b"%PDF")
    assert (
        content.count(b"/Type /Page\n") + content.count(b"/Type /Page ") + content.count(b"/Type/Page") >= 1
    )


def test_stacks_only_passes_stack_serials(dashboard):
    dashboard.switch.getNetworkSwitchStacks.side_effect = lambda network_id: (
        [{"serials": ["Q-1", "Q-9"]}] if network_id == "N_1" else []
    )
    dashboard.switch.getOrganizationSwitchPortsUsageHistoryByDeviceByInterval.return_value = {"items": []}

    tool.main(["--stacks-only"])

    kwargs = dashboard.switch.getOrganizationSwitchPortsUsageHistoryByDeviceByInterval.call_args.kwargs
    assert kwargs["serials"] == ["Q-1", "Q-9"]


def test_no_data_writes_no_file(dashboard, isolated_env):
    dashboard.switch.getOrganizationSwitchPortsUsageHistoryByDeviceByInterval.return_value = {"items": []}
    assert tool.main([]) == 0
    assert not list((isolated_env / "output" / "port_utilization_report").glob("*.pdf"))


def test_days_limit():
    with pytest.raises(SystemExit):
        tool.main(["--days", "40"])
