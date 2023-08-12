# remove_stp.py

"""
Disable RSTP and enable BPDUGuard on all access ports
"""

import json
import meraki
import os
from pathlib import Path
from pprint import pprint
import logging
from meraki_utils import connect_to_meraki, meraki_error, other_error

# Constants
API_KEY = os.getenv('MERAKI_API_KEY')
LOG_PATH = Path('logs')

# Variables

if not LOG_PATH.exists():
    LOG_PATH.mkdir(parents=True)

# Get script file name and strip the .py extension
script_name = os.path.basename(__file__)
script_name = os.path.splitext(script_name)[0]
log_file_name = f"{script_name}.log"
logging.basicConfig(filename=f'logs/{log_file_name}',
                    level=logging.WARNING,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

dashboard = connect_to_meraki(API_KEY)

# List for added action batches
actions = []

# Get organizations
print(f"Obtaining organizations...")
logging.info(f'Obtaining organizations...')
try:
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    meraki_error(e)
    logging.error(e)
    exit(1)
except Exception as e:
    other_error(e)
    logging.error(e)
    exit(1)

# Get networks
print(f"Obtaining networks in Organization: {organizations[0]['name']}.")
try:
    networks = dashboard.organizations.getOrganizationNetworks(organizationId=organizations[0]['id'])
except meraki.APIError as e:
    meraki_error(e)
    logging.error(e)
    exit(1)
except Exception as e:
    other_error(e)
    logging.error(e)
    exit(1)

networks = [n for n in networks if 'switch' in n['productTypes']]

# For each network, get all Meraki devices
for network in networks:
    print(f"Obtaining switches in network: {network['name']}.")
    try:
        switches = dashboard.networks.getNetworkDevices(networkId=network['id'])
    except meraki.APIError as e:
        meraki_error(e)
        logging.error(e)
        exit(1)
    except Exception as e:
        other_error(e)
        logging.error(e)
        exit(1)

    # Remove all non-switch devices
    switches = [s for s in switches if 'MS' in s['model']]

    for switch in switches:
        # Get all ports on the switch
        print(f"Obtaining ports on switch {switch['name']} on the {network['name']} network.")
        try:
            switch_ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
        except meraki.APIError as e:
            meraki_error(e)
            logging.error(e)
            exit(1)
        except Exception as e:
            other_error(e)
            logging.error(e)
            exit(1)

        # iterate over the ports and configure appropriate STP settings
        for port in switch_ports:
            if port['type'] == 'access':
                # If Access port, disable RSTP and enable BPDU Guard
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
                    logging.info(f"Added port {port['portId']} on switch {switch['name']} to action batch.")
            elif port['type'] == 'trunk':
                # If Trunk port, enable RSTP and disable BPDU Guard
                if len(actions) < 100:
                    actions.append(
                        {
                            'resource': f"/devices/{switch['serial']}/switch/ports/{port['portId']}",
                            'operation': 'update',
                            'body': {
                                'rstpEnabled': True,
                                'stpGuard': 'disabled'
                            }
                        }
                    )
                    logging.info(f"Added port {port['portId']} on switch {switch['name']} to action batch.")


        if len(actions) >= 1:
            try:
                print(f"Sending action batch to Meraki for processing.")
                response = dashboard.organizations.createOrganizationActionBatch(
                    organizationId=organizations[0]['id'],
                    actions=actions,
                    confirmed=True,
                    synchronous=False
                )
                logging.info(f"Action batch complete.")
                actions = []
            except Exception as e:
                logging.error(f"Unable to perform action batch on switch {switch['name']}. Error: {e}")
                exit(1)
