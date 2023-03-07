# tag_all_trunk_ports.py

"""
Add a tag to all trunk ports
"""

import os
import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error

API_KEY = os.getenv('MERAKI_API_KEY')

actions = []

dashboard = connect_to_meraki(API_KEY)

# Get organizations
try:
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    meraki_error(e)
except Exception as e:
    other_error(e)

# Get networks for each organization
for org in organizations:
    try:
        networks = dashboard.organizations.getOrganizationNetworks(organizationId=org['id'])
    except meraki.APIError as e:
        meraki_error(e)
    except Exception as e:
        other_error(e)

    # Only retain networks that contain switches
    networks = [n for n in networks if 'switch' in n['productTypes']]

    # Get all the devices on each network
    for network in networks:
        try:
            devices = dashboard.networks.getNetworkDevices(networkId=network['id'])
        except meraki.APIError as e:
            meraki_error(e)
        except Exception as e:
            other_error()

        # Only interested in the Switch devices
        switches = [d for d in devices if d['model'].startswith('MS')]

        for switch in switches:
            try:
                switch_ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
            except meraki.APIError as e:
                meraki_error(e)
            except Exception as e:
                other_error(e)

            switch_trunk_ports = [port for port in switch_ports if port['type'] == 'trunk' if port['vlan'] == 1001]

            for port in switch_trunk_ports:
                if len(actions) < 100:
                    actions.append(
                        {
                            'resource': f"devices/{switch['serial']}/switch/ports/{port['portId']}",
                            'operation': 'update',
                            'body': {
                                'tags': ['Trunk']
                            }
                        }
                    )

            if len(actions) >= 1:
                response = dashboard.organizations.createOrganizationActionBatch(
                    organizationId=org['id'],
                    actions=actions,
                    confirmed=True,
                    synchronous=False
                )