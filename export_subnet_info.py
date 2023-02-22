# export_subnet_info.py

"""
Exports all info regarding switch subnets and interfaces to a json file
"""

import meraki
import os
import json

from meraki_utils import connect_to_meraki, meraki_error, other_error

API_KEY = os.getenv('MERAKI_API_KEY')

# Connect to Meraki dashboard
dashboard = connect_to_meraki(API_KEY)

subnets = {}

# Attempt to obtain organizations
try:
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    meraki_error(e)
except Exception as e:
    other_error(e)

# Loop through the organizations
for org in organizations:
    # Attempt to obtain all networks in the organization
    try:
        networks = dashboard.organizations.getOrganizationNetworks(organizationId=org['id'])
    except meraki.APIError as e:
        meraki_error(e)
    except Exception as e:
        other_error(e)

    # Drop networks that don't contain switches
    networks = [n for n in networks if 'switch' in n['productTypes']]

    # For each network get all the Meraki devices
    for net in networks:
        try:
            devices = dashboard.networks.getNetworkDevices(networkId=net['id'])
        except meraki.APIError as e:
            meraki_error(e)
        except Exception as e:
            other_error(e)


        # Discard all devices other than switches
        devices = [d for d in devices if 'MS' in d['model']]

        # For each switch get the routing interface
        for device in devices:
            device_subnet = {}
            try:
                current_subnet = dashboard.switch.getDeviceSwitchRoutingInterfaces(serial=device['serial'])
            except meraki.APIError as e:
                meraki_error(e)
            except Exception as e:
               other_error(e)

            # Append list of interfaces to subnet dictionary
            subnets[device['name']] = current_subnet

print(subnets)