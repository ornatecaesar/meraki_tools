import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error
import os
from pathlib import Path
from pprint import pprint

# Constants
API_KEY = os.getenv('MERAKI_API_KEY')
LOG_PATH = Path('logs')

# Connect to dashboard
dashboard = connect_to_meraki(API_KEY)

# Get organization
try:
    organization = dashboard.organizations.getOrganizations()[0]
except meraki.APIError as e:
    meraki_error(e)
except Exception as e:
    other_error(e)

# Get networks in organization
try:
    networks = dashboard.organizations.getOrganizationNetworks(organizationId=organization['id'])
except meraki.APIError as e:
    meraki_error(e)
    exit(1)
except Exception as e:
    other_error(e)
    exit(1)

networks = [n for n in networks if 'College' in n['name']]

# For each network get all Meraki devices
for network in networks:
    print(f"Obtaining devices for network {network['name']}")
    try:
        switches = dashboard.networks.getNetworkDevices(networkId=network['id'])
    except meraki.APIError as e:
        meraki_error(e)
        exit(1)
    except Exception as e:
        other_error(e)
        exit(1)

    # Remove non-switches from results
    switches = [s for s in switches if 'MS' in s['model'] if 'IT' in s['tags']]

    for switch in switches:
        #Get all ports on the switch
        try:
            switch_ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
        except meraki.APIError as e:
            meraki_error(e)
            exit(1)
        except Exception as e:
            other_error(e)
            exit(1)

        for port in switch_ports:

            if 'DL_DESK' in port['tags']:
                switch_port_config = {
                    'enabled': True,
                    'poeEnabled': True,
                    'type': 'trunk',
                    'vlan': 16,
                    'allowedVlans': '16,150,700-701,790',

                }

                print(f"Switch: {switch['name']}")
                print(f"Port #: {port['portId']}")
                print(f"Port name: {port['name']}")

