import os
from pathlib import Path
import logging
import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error

API_KEY = os.getenv('MERAKI_API_KEY')

# Logging
logging_dir = Path('logs')
if not logging_dir.exists():
    logging_dir.mkdir(parents=True)

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
            other_error(e)


        # Only interested in the Switch devices
        switches = [d for d in devices if d['model'].startswith('MS')]

        for switch in switches:
            try:
                switch_ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
            except meraki.APIError as e:
                meraki_error(e)
            except Exception as e:
                other_error(e)

            # Only interested in the ports have native VLAN 16
            ports = [p for p in switch_ports if p['type'] == 'trunk' if p['vlan'] == 16]


