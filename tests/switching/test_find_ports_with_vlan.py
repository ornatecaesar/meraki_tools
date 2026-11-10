import pytest

from meraki_tools.switching import find_ports_with_vlan as tool
from tests.conftest import make_port, make_switch


@pytest.mark.parametrize(
    ("port", "expected"),
    [
        (make_port(1, vlan=100), "access"),
        (make_port(1, vlan=5, voiceVlan=100), "voice"),
        (make_port(1, vlan=5), None),
        (make_port(1, type="trunk", vlan=100, allowedVlans="100,200"), "native"),
        (make_port(1, type="trunk", vlan=1, allowedVlans="1,90-110"), "allowed"),
        (make_port(1, type="trunk", vlan=1, allowedVlans="1,2"), None),
        (make_port(1, type="trunk", vlan=100, allowedVlans="all"), None),
    ],
)
def test_match_reason(port, expected):
    assert tool.match_reason(port, 100) == expected


def test_all_trunks_included_on_request():
    port = make_port(1, type="trunk", allowedVlans="all")
    assert tool.match_reason(port, 100, include_all_trunks=True) == "allowed (all)"


def test_csv_written_to_output_folder(dashboard, isolated_env, capsys):
    dashboard.switch.getOrganizationSwitchPortsBySwitch.return_value = [
        make_switch("SW1", "Q-1", [make_port(1, vlan=100, name="Printer"), make_port(2)]),
    ]

    assert tool.main(["100", "--csv"]) == 0

    assert "Printer" in capsys.readouterr().out
    (csv_file,) = (isolated_env / "output" / "find_ports_with_vlan").glob("vlan_100_ports_*.csv")
    lines = csv_file.read_text().splitlines()
    assert lines[0].startswith("network,switch,port")
    assert len(lines) == 2
