from meraki_tools.switching import remove_stp
from tests.conftest import make_port, make_switch, sent_actions


def _ports():
    return [
        make_port(1),  # access, RSTP on: needs change
        make_port(2, rstpEnabled=False, stpGuard="bpdu guard"),  # already compliant
        make_port(3, type="trunk"),  # trunks are left alone
    ]


def test_needs_change():
    access, done, trunk = _ports()
    assert remove_stp.needs_change(access)
    assert not remove_stp.needs_change(done)
    assert not remove_stp.needs_change(trunk)


def test_dry_run_by_default_sends_nothing(dashboard):
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [make_switch("SW1", "Q-1", _ports())]

    assert remove_stp.main([]) == 0
    dashboard.organizations.createOrganizationActionBatch.assert_not_called()


def test_apply_updates_only_noncompliant_access_ports(dashboard):
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [make_switch("SW1", "Q-1", _ports())]

    assert remove_stp.main(["--apply"]) == 0
    assert sent_actions(dashboard) == [
        {
            "resource": "/devices/Q-1/switch/ports/1",
            "operation": "update",
            "body": {"rstpEnabled": False, "stpGuard": "bpdu guard"},
        }
    ]


def test_network_filter_is_passed_to_the_api(dashboard):
    remove_stp.main(["--network", "annex", "--switch", "SW"])

    kwargs = dashboard.switch.getOrganizationSwitchPortsBySwitch.call_args.kwargs
    assert kwargs["networkIds"] == ["N_2"]
    assert kwargs["name"] == "SW"


def test_unknown_network_matches_nothing(dashboard):
    assert remove_stp.main(["--network", "nowhere", "--apply"]) == 0
    dashboard.switch.getOrganizationSwitchPortsBySwitch.assert_not_called()


def test_failed_batch_gives_nonzero_exit(dashboard):
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [make_switch("SW1", "Q-1", _ports())]
    dashboard.organizations.createOrganizationActionBatch.return_value = {
        "id": "B",
        "status": {"failed": True},
    }

    assert remove_stp.main(["--apply"]) == 1
