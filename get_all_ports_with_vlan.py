import os
import logging
from pathlib import Path
import meraki

from meraki_utils import connect_to_meraki, meraki_error, other_error

API_KEY = os.environ.get('MERAKI_API_KEY')
# LOG_PATH = Path('logs')
#
# if not LOG_PATH.exists():
#     LOG_PATH.mkdir(parents=True)

# Configure logging
script_name = os.path.splitext(os.path.basename(__file__))[0]
logging.basicConfig(filename=f'logs/{script_name}',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
meraki_logger = logging.getLogger('meraki')
meraki_logger.setLevel(logging.INFO)


# Variables
vlan_of_interest = 35

# Create a Dashboard session
dashboard = connect_to_meraki(API_KEY)


# Get organizations
try:
    meraki_logger.info('Obtaining organizations...')
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    meraki_logger.error(e)
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
    networks = [s for s in networks if 'switch' in s['productTypes']]

    # Get all the devices on each network
    for network in networks:
        try:
            devices = dashboard.networks.getNetworkDevices(networkId=network['id'])
        except meraki.APIError as e:
            meraki_error(e)
