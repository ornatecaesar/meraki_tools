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

actions = []
vlan_to_add = 2000

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
        switches = [s for s in switches if 'KBG' in s['name']]

        for switch in switches:
            try:
                switch_ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
            except meraki.APIError as e:
                meraki_error(e)
            except Exception as e:
                other_error(e)

            # For each port, check if it is a Trunk and has native VLAN 16
            for port in switch_ports:
                if port['portId'] == '18':
                    if port['type'] == 'trunk' and port['vlan'] == 16:
                        # Add the port to the action batch if the action batch is less than 100, the API limit
                        if len(actions) < 100:
                            logging.info(f"Adding port {port['portId']} on switch {switch['name']} to action batch.")
                            # Get currently allowed VLANs on the port
                            allowed_vlans = port['allowedVlans']
                            # Add VLAN 16 to the allowed VLANs
                            allowed_vlans += f",{vlan_to_add}"
                            actions.append(
                                {
                                    "resource": f"/devices/{switch['serial']}/switch/ports/{port['portId']}",
                                    'operation': 'update',
                                    'body': {
                                        'allowedVlans': allowed_vlans
                                    }
                                }
                            )

            if len(actions) >= 1:
                try:
                    logging.info(f"Executing Action Batch")
                    response = dashboard.organizations.createOrganizationActionBatch(
                        organizationId=org['id'],
                        actions=actions,
                        confirmed=True,
                        synchronous=True
                    )
                except meraki.APIError as e:
                    logging.error(f"Unable to execute action batch: {e}")

                actions = []

        logging.info(f"Completed processing Action Batch.")
