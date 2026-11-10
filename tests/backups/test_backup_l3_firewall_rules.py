import json

from meraki_tools.backups import backup_l3_firewall_rules as tool


def test_safe_filename():
    assert tool.safe_filename("A/B  C") == "A_B_C"
    assert tool.safe_filename("///") == "network"


def test_backs_up_each_appliance_network_and_policy_objects(dashboard, isolated_env):
    dashboard.organizations.getOrganizationNetworks.return_value = [
        {"id": "N_1", "name": "Head Office"},
        {"id": "N_2", "name": "Branch"},
    ]
    dashboard.appliance.getNetworkApplianceFirewallL3FirewallRules.return_value = {
        "rules": [{"policy": "deny", "protocol": "any", "srcCidr": "Any", "destCidr": "192.0.2.0/24"}]
    }
    dashboard.organizations.getOrganizationPolicyObjects.return_value = [{"id": "1", "name": "Printers"}]
    dashboard.organizations.getOrganizationPolicyObjectsGroups.return_value = []

    assert tool.main(["--network", "head"]) == 0

    (folder,) = (isolated_env / "output" / "backup_l3_firewall_rules").iterdir()
    names = sorted(p.name for p in folder.iterdir())
    assert names == ["Head_Office_l3_firewall_rules.json", "policy_object_groups.json", "policy_objects.json"]
    saved = json.loads((folder / "Head_Office_l3_firewall_rules.json").read_text())
    assert saved["network"]["name"] == "Head Office"
    assert saved["rules"][0]["policy"] == "deny"
    dashboard.organizations.getOrganizationNetworks.assert_called_with(
        "O_1", productTypes=["appliance"], total_pages="all"
    )


def test_no_appliance_networks_is_not_an_error(dashboard, isolated_env):
    dashboard.organizations.getOrganizationNetworks.return_value = []
    assert tool.main([]) == 0
    assert not (isolated_env / "output" / "backup_l3_firewall_rules").exists()
