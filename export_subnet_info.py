# export_subnet_info.py

"""
Exports all info regarding switch subnets and interfaces to a json file
"""
import pathlib

import meraki
import os
import json

import pandas as pd

from meraki_utils import connect_to_meraki, meraki_error, other_error

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# Connect to Meraki dashboard
dashboard = connect_to_meraki()

interface_info_df = pd.DataFrame(columns=['name', 'subnet', 'interfaceIp', 'vlanId', 'switch', 'network'])

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

    # For each network
    # Get all stacks on the network
    for net in networks:
        try:
            stacks = dashboard.switch.getNetworkSwitchStacks(networkId=net['id'])
        except meraki.APIError as e:
            meraki_error(e)
        except Exception as e:
            other_error(e)

        # Get all devices on the network
        try:
            devices = dashboard.networks.getNetworkDevices(networkId=net['id'])
        except meraki.APIError as e:
            meraki_error(e)
        except Exception as e:
            other_error(e)

        # Discard all non-switch devices
        devices = [d for d in devices if d['model'].startswith('MS')]

        # Get set of all serial numbers of switches that are members of stacks
        stack_serials = {serial for stack in stacks for serial in stack['serials']}

        # Check if the serial number of a switch is a stack member. If not, get the L3 interface info
        for device in devices:
            if device['serial'] not in stack_serials:
                l3_interface_info = dashboard.switch.getDeviceSwitchRoutingInterfaces(serial=device['serial'])
                for l3_interface in l3_interface_info:
                    interface_info_df = interface_info_df._append({
                        'name': l3_interface['name'],
                        'subnet': l3_interface['subnet'],
                        'interfaceIp': l3_interface['interfaceIp'],
                        'vlanId': l3_interface['vlanId'],
                        'switch': device['name'],
                        'network': net['name']
                    }, ignore_index=True)

        for stack in stacks:
            l3_interface_info = dashboard.switch.getNetworkSwitchStackRoutingInterfaces(networkId=net['id'], switchStackId=stack['id'])
            for l3_interface in l3_interface_info:
                interface_info_df = interface_info_df._append({
                    'name': l3_interface['name'],
                    'subnet': l3_interface['subnet'],
                    'interfaceIp': l3_interface['interfaceIp'],
                    'vlanId': l3_interface['vlanId'],
                    'switch': stack['name'],
                    'network': net['name']
                }, ignore_index=True)


# Ensure directory exists
export_dir = pathlib.Path('csv_exports')
export_dir.mkdir(parents=True, exist_ok=True)

# Export dataframe to csv
interface_info_df.to_csv(export_dir / 'interface_info_df.csv', header=True, index=False)
