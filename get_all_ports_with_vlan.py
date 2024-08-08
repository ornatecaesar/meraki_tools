import os
from pathlib import Path
import logging
import meraki
import pandas as pd
from meraki_utils import connect_to_meraki, meraki_error, other_error

# Set Pandas display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None)

API_KEY = os.getenv('MERAKI_API_KEY')

# Logging
logging_dir = Path('logs')
if not logging_dir.exists():
    logging_dir.mkdir(parents=True)

# Configure log file names, level and content
script_name = os.path.basename(__file__)
script_name = os.path.splitext(script_name)[0]
log_file_name = f"{script_name}.log"
logging.basicConfig(filename=f'logs/{log_file_name}',
                    level=logging.WARNING,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger('meraki').setLevel(logging.WARNING)

df_switch_details = pd.DataFrame(columns=['Switch Name', 'Port Number', 'Port Type'])


def is_vlan_in_list(vlan, vlan_list_string):
    """
    Checks if the WiFi management vlan number is within the allowedVLan list including with a vlan range
    :param vlan: Existing VLAN contained within the allowedVlan list. In this case WiFi Management VLAN 16
    :param vlan_list_string: The list
    :return: Boolean
    """
    # If allowedVlans contains 'all', no need to add it to add the additional VLAN
    if 'all' in vlan_list_string.lower():
        return False

    vlan_list = vlan_list_string.split(',')

    for item in vlan_list:
        if '-' in item:
            range_start, range_end = item.split('-')
            if int(range_start) <= vlan <= int(range_end):
                return True
        else:
            if int(item) == vlan:
                return True

    return False

vlan_to_find = 20

dashboard = meraki.DashboardAPI(api_key=API_KEY,
                                print_console=False,
                                output_log=True,
                                inherit_logging_config=True,
                                log_file_prefix=f'{__file__}')

# Get organizations
try:
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    logging.info(f"{e}")
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
    networks = [n for n in networks if 'switch' in n['productTypes'] and 'junior' in n['name'].lower()]

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


            for port in switch_ports:
                if port['type'] == 'trunk':
                    # If the current port is a trunk, look for VLAN number in multiple attributes of the port
                    if ((port['vlan'] == vlan_to_find and 'all' not in port['allowedVlans']) or
                            (port['vlan'] == 1001 and is_vlan_in_list(vlan_to_find, port['allowedVlans']) == True)):

                        # Add switch port details to dataframe
                        df_switch_details = df_switch_details._append({
                            'Switch Name': switch['name'],
                            'Port Number': port['portId'],
                            'Port Type': port['type']
                        }, ignore_index=True)
                elif port['type'] == 'access':
                    # If the current port is an access port, check if the 'vlan' attribute mathces the vlan_to_find
                    if port['vlan'] == vlan_to_find:
                        df_switch_details = df_switch_details._append({
                            'Switch Name': switch['name'],
                            'Port Number': port['portId'],
                            'Port Type': port['type']
                        }, ignore_index=True)

print(df_switch_details)






