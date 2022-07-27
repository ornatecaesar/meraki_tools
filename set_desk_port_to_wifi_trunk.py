import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error
import os
from pathlib import Path

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
except Exception as e:
    other_error(e)

