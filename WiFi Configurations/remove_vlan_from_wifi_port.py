import os
from pathlib import Path
import logging
import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error

API_KEY = os.getenv('MERAKI_API_KEY')

# Logging
logging_dir = Path('../logs')
if not logging_dir.exists():
    logging_dir.mkdir(parents=True)

# Configure log file names, level and content
script_name = os.path.basename(__file__)
script_name = os.path.splitext(script_name)[0]
log_file_name = f"{script_name}.log"
logging.basicConfig(filename=f'../logs/{log_file_name}',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger('meraki').setLevel(logging.WARNING)

actions = []
vlan_to_remove = 700


def is_vlan_in_list(vlan, vlan_list_string):
    """
    Checks if the WiFi management vlan number is within the allowedVlan list including with a vlan range
    :param vlan: Existing VLAN contained within the allowedVlan list. In this case WiFi Management VLAN 16
    :param vlan_list_string: The list
    :return: Boolean
    """
    # If allowedVlans contains 'all', treat as not matching for our targeting logic
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


def remove_vlan_from_list(vlan, vlan_list_string):
    """
    Removes the specified VLAN from the allowedVlans string.
    Handles VLAN ranges by splitting them appropriately if the VLAN to remove is inside a range.
    Returns the updated allowedVlans string if a change was made, otherwise returns the original string.
    If the result would be empty, returns the original (to avoid invalid empty allowedVlans).
    """
    if 'all' in vlan_list_string.lower():
        return vlan_list_string

    parts = [p.strip() for p in vlan_list_string.split(',') if p.strip()]
    new_parts = []
    removed = False

    for part in parts:
        if '-' in part:
            try:
                range_start, range_end = map(int, part.split('-'))
                if range_start <= vlan <= range_end:
                    removed = True
                    if range_start < vlan:
                        left = f"{range_start}-{vlan - 1}"
                        if range_start == vlan - 1:   # single VLAN left → collapse
                            left = str(range_start)
                        new_parts.append(left)
                    if vlan < range_end:
                        right = f"{vlan + 1}-{range_end}"
                        if vlan + 1 == range_end:     # single VLAN right → collapse
                            right = str(vlan + 1)
                        new_parts.append(right)
                else:
                    new_parts.append(part)
            except ValueError:
                new_parts.append(part)
        else:
            try:
                if int(part) == vlan:
                    removed = True
                    # do not append - effectively removing it
                else:
                    new_parts.append(part)
            except ValueError:
                new_parts.append(part)

    if removed:
        new_allowed = ','.join(new_parts)
        if new_allowed.strip():  # only return non-empty result
            return new_allowed
        else:
            # Would result in empty allowedVlans - keep original to avoid invalid config
            return vlan_list_string
    else:
        return vlan_list_string


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

        # Only interested in the Switch devices matching naming convention
        switches = [d for d in devices if d['model'].startswith('MS')]
        switches = [s for s in switches if 'C-SW' in s['name']]

        for switch in switches:
            try:
                switch_ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
            except meraki.APIError as e:
                meraki_error(e)
            except Exception as e:
                other_error(e)

            for port in switch_ports:

                if (port['type'] == 'trunk' and (
                        (port['vlan'] == 16 and 'all' not in port['allowedVlans']) or
                        (port['vlan'] == 1001 and is_vlan_in_list(16, port['allowedVlans']) == True))):

                    new_allowed_vlans = remove_vlan_from_list(vlan_to_remove, port['allowedVlans'])

                    if new_allowed_vlans != port['allowedVlans']:
                        logging.info(f"Removing VLAN {vlan_to_remove} from port {port['portId']} on switch {switch['name']}. "
                                     f"Old allowedVlans: {port['allowedVlans']} -> New: {new_allowed_vlans}")

                        # Add update to action batch
                        actions.append(
                            {
                                "resource": f"/devices/{switch['serial']}/switch/ports/{port['portId']}",
                                'operation': 'update',
                                'body': {
                                    'allowedVlans': new_allowed_vlans
                                }
                            }
                        )

                        # If the number of actions in the batch is 20, execute the action batch
                        if len(actions) == 20:
                            try:
                                logging.info(f"Executing Action Batch with 20 actions.")
                                response = dashboard.organizations.createOrganizationActionBatch(
                                    organizationId=org['id'],
                                    actions=actions,
                                    confirmed=True,
                                    synchronous=True
                                )
                                logging.info(f"Completed processing Action Batch.")
                                actions = []
                            except meraki.APIError as e:
                                logging.error(f"Unable to execute action batch: {e}")
                                actions = []  # Reset actions even if batch execution fails
                            except Exception as e:
                                logging.error(f"An unexpected error occurred: {e}")
                                actions = []

    # After all loops for this organization, execute any remaining actions
    if actions:
        try:
            logging.info(f"Executing Final Action Batch with {len(actions)} actions for org {org['id']}.")
            response = dashboard.organizations.createOrganizationActionBatch(
                organizationId=org['id'],
                actions=actions,
                confirmed=True,
                synchronous=True
            )
            logging.info(f"Completed final Action Batch.")
            actions = []
        except meraki.APIError as e:
            logging.error(f"Unable to execute final action batch: {e}")
            actions = []
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            actions = []