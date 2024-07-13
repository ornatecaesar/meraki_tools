# remove_vlan_from_trunks.py

"""
Removes the specified VLAN from the Routing & DHCP configuration of Switches,
then removes the specified VLAN from all trunks that have the VLAN in the
Allowed VLANs list
"""

import os
from pathlib import Path
import logging
import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error

API_KEY = os.environ.get('MERAKI_API_KEY')

# Configure logging directory
logging_dir = Path('logs')
if not logging_dir.exists():
    logging_dir.mkdir(parents=True)

# Configure logging filename, level and content
script_name = os.path.basename(__file__)
script_name = os.path.splitext(script_name)[0]
log_file_name = f'{script_name}.log'
logging.basicConfig(filename=f'logs/{log_file_name}',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger('meraki').setLevel(logging.INFO)

actions = []
vlan_to_remove = 701


def is_vlan_in_list(vlan, vlan_list_string):
    """
        Checks if the vlan number is within the allowedVlan list including with a vlan range
        :param vlan: VLAN contained within the allowedVlan list. This is the VLAN to remove.
        :param vlan_list_string: The existing VLAN allowed list
        :return: Boolean
    """
    # Ignore condition if 'all' is in allowedVlans
    if 'all' in vlan_list_string.lower():
        return False

    vlan_list = vlan_list_string.split(',')

    for item in vlan_list:
        # If the VLAN is contained within a VLAN range, return true
        if '-' in item:
            range_start, range_end = item.split(',')
            if int(range_start) <= vlan <= int(range_end):
                return True
        # If the VLAN is specifically listed, return True
        elif int(item) == vlan:
            return True

    # Return false in all other circumstances
    return False

dashboard = connect_to_meraki(API_KEY)

try:
    logging.info('Creating Dashboard session.')
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as error:
    print(meraki_error(error))
    logging.error(error)
except Exception as error:
    print(other_error(error))
    logging.error(error)

for org in organizations:
    # Get organizatiosn networks
    try:
        logging.info(f'Getting networks for {org["name"]}')
        networks = dashboard.organizations.getOrganizationNetworks(organizationId=org['id'])
    except meraki.APIError as error:
        logging.error(error)
    except Exception as error:
        logging.error(error)

    networks = [n for n in networks if 'switch' in n['productTypes']]

    for network in networks:
        try:
            devices = dashboard.networks.getNetworkDevices(networkId=network['id'])
        except meraki.APIError as error:
            logging.error(error)
        except Exception as error:
            logging.error(error)

        devices = [d for d in devices if d['model'].startswith('MS')]
