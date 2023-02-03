# remove_stp.py

"""
Disable RSTP and enable BPDUGuard on all access ports
"""

import json
import meraki
import os
from pathlib import Path
from pprint import pprint

from meraki_utils import connect_to_meraki, meraki_error, other_error


# Constants
API_KEY = os.getenv('MERAKI_API_KEY')
LOG_PATH = Path('logs')

if not LOG_PATH.exists():
    LOG_PATH.mkdir(parents=True)

dashboard = connect_to_meraki(API_KEY)

batch_actions = []

# Get organizations
print(f"Obtaining organizations...")
try:
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    meraki_error(e)
    exit(1)
except Exception as e:
    other_error(e)
    exit(1)

# Get networks
print(f"Obtaining networks in Organization: {organizations[0]['name']}.")
try:
    networks = dashboard.organizations.getOrganizationNetworks(organizationId=organizations[0]['id'])
except meraki.APIError as e:
    meraki_error(e)
    exit(1)
except Exception as e:
    other_error(e)
    exit(1)

networks = [n for n in networks if 'switch' in n['productTypes']]

# For each network, get all Meraki devices

for network in networks:
    print(f"Obtaining switches in network: {network['name']}.")
    try:
        switches = dashboard.networks.getNetworkDevices(networkId=network['id'])
    except meraki.APIError as e:
        meraki_error(e)
        exit(1)
    except Exception as e:
        other_error(e)
        exit(1)

    # Remove all non-switch devices
    switches = [s for s in switches if 'MS' in s['model']]
    switches = [s for s in switches if 'JSW' in s['name']]

    for switch in switches:
        # Get all ports on the switch
        print(f"Obtaining ports on switch {switch['name']} on the {network['name']} network.")
        try:
            switch_ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
        except meraki.APIError as e:
            meraki_error(e)
            exit(1)
        except Exception as e:
            other_error(e)
            exit(1)

        for port in switch_ports:

            #TODO: Convert to Action Batch
            if port['type'] == 'access':

                # Loop through ports. If access port, add to action batch
                if len(batch_actions) < 100:
                    batch_actions.append(
                        {
                            'resource': f"/devices/{switch['serial']}/switch/ports/{port['portId']}",
                            'operation': 'update',
                            'body': {
                                'rstpEnabled': False,
                                'stpGuard': 'bpdu guard'
                            }
                        }
                    )

        # Run action batch
        if len(batch_actions) >= 1:
            response = dashboard.organizations.createOrganizationActionBatch(
                organizationId=organizations[0]['id'],
                actions=batch_actions,
                confirmed=True,
                synchronous=False
            )
            print(response)
        # print(f"{switch['name']} action batch size: {len(batch_actions)}")
        #pprint(batch_actions, indent=4)
        batch_actions = []
                # New port configuration
                # switch_port_conf = {
                #     'rstpEnabled': False,
                #     'stpGuard': 'bpdu guard'
                # }
                #
                # # Update switchport with new config
                # print(f"Updating configuration on port {port['portId']}.")
                # try:
                #     new_port_config = dashboard.switch.updateDeviceSwitchPort(switch['serial'], port['portId'],
                #                                                               **switch_port_conf)
                #
                # except meraki.APIError as e:
                #     meraki_error(e)
                #     exit(1)
                # except AssertionError as e:
                #     print(e)
                #     exit(1)
                #
                # # if the port update was successful display the new config from the update response
                # #TODO: Improve verfication check to ensure not checking against a previous port
                # if new_port_config['portId'] == port['portId']:
                #     if new_port_config['rstpEnabled'] == switch_port_conf['rstpEnabled'] or \
                #             new_port_config['stpGuard'] == switch_port_conf['stpGuard']:
                #         print(f"New Configuration updated on port {port['portId']} on {switch['name']}:")
                #         print(f"\tRSTP Status:      {new_port_config['rstpEnabled']}")
                #         print(f"\tSTP Guard Mode:   {new_port_config['stpGuard']}")


