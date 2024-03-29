import os
from pprint import pprint
import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error


API_KEY = os.getenv('MERAKI_API_KEY')
vlan_of_interest = 999
target_network = {'College'}

dashboard = connect_to_meraki(API_KEY)

action_batch = {
    'confirmed': True,
    'synchronous': False,
    'actions': [

    ]
}

print(f"Getting organizations...")
try:
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    meraki_error(e)
    exit(1)
except Exception as e:
    other_error(e)
    exit(1)

print(f"Obtaining networks for organization: {organizations[0]['name']}")
try:
    networks = dashboard.organizations.getOrganizationNetworks(organizationId=organizations[0]['id'])
except meraki.APIError as e:
    meraki_error(e)
    exit(1)
except Exception as e:
    other_error(e)
    exit(1)

# Remove networks without switches
networks = [n for n in networks if 'switch' in n['productTypes']]

for network in networks:

    print(f"Obtaining switches in network: {network['name']}")
    try:
        switches = dashboard.networks.getNetworkDevices(networkId=network['id'])
    except meraki.APIError as e:
        meraki_error(e)
        exit(1)
    except Exception as e:
        other_error(e)
        exit(1)

    switches = [s for s in switches if 'MS' in s['model']]

    for switch in switches:
        print(f"Obtaining ports on switch \'{switch['name']}\' in network \'{network['name']}\'")
        try:
            ports = dashboard.switch.getDeviceSwitchPorts(serial=switch['serial'])
        except meraki.APIError as e:
            meraki_error(e)
            exit(1)
        except Exception as e:
            other_error(e)
            exit(1)

        access_ports = ([p for p in ports if p['vlan'] == vlan_of_interest if p['type'] == 'access'])
        if len(access_ports) > 0:
            for port in access_ports:
                actions = {
                    'resource': f"/devices/{switch['serial']}/switch/ports/{str(port['portId'])}",
                    'operation': 'update',
                    'body': {'vlan': 1}
                    }
                action_batch['actions'].append(actions)



try:
    dashboard.organizations.createOrganizationActionBatch(organizationId=organizations[0]['id'], actions=action_batch)
except meraki.APIError as e:
    meraki_error(e)
    exit(1)
except Exception as e:
    other_error(e)
    exit(1)


