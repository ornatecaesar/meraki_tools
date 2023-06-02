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

# Variables

if not LOG_PATH.exists():
    LOG_PATH.mkdir(parents=True)

dashboard = connect_to_meraki(API_KEY)

# List for added action batches
actions = []

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
    switches = [s for s in switches if 'CSWSBU01' in s['name']]

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

        # iterate over the ports and if the current port is an access port, add the port to the action batch
        for port in switch_ports:
            if port['type'] == 'access':
                if len(actions) < 100:
                    actions.append(
                        {
                            'resource': f"/devices/{switch['serial']}/switch/ports/{port['portId']}",
                            'operation': 'update',
                            'body': {
                                'rstpEnabled': False,
                                'stpGuard': 'bpdu guard'
                            }
                        }
                    )

        if len(actions) >= 1:
            response = dashboard.organizations.createOrganizationActionBatch(
                organizationId=organizations[0]['id'],
                actions=actions,
                confirmed=True,
                synchronous=False
            )

        pprint(response, indent=4)
