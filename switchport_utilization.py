import meraki
import pandas as pd
import time
from datetime import datetime
import sqlite3

from meraki_utils import connect_to_meraki

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

dashboard = connect_to_meraki()

records = []

# Get organizations
orgs = dashboard.organizations.getOrganizations()
org_id = orgs[0]['id']

# Get networks
networks = dashboard.organizations.getOrganizationNetworks(organizationId=org_id,
                                                           productTypes=['switch'])

# Create network lookup table
network_lookup = {net['id']: net['name'] for net in networks}

# Get switches
switches = dashboard.organizations.getOrganizationDevices(organizationId=org_id,
                                                         productTypes=['switch'])

for switch in switches:
    print(f"Processing {switch['name']}")
    serial = switch['serial']
    network_id = switch.get('networkId')
    network_name = network_lookup.get(network_id, "Unbounded") if network_id else "No Network"
    device_name = switch.get('name', serial)

    # Get each ports status
    try:
        ports = dashboard.switch.getDeviceSwitchPortsStatuses(serial=serial,
                                                              timespan=86400)
    except meraki.APIError as e:
        print(f"  ⚠️ Error on {serial}: {e}")

    for port in ports:
        print(f"  Processing port {port['portId']}")
        usage = port.get('usageInKb', {})
        recv_mbps = round(usage.get('recv', 0) / 1000, 3)
        sent_mbps = round(usage.get('sent', 0) / 1000, 3)
        total_mbps = round(usage.get('total', 0) / 1000, 3)

        # CDP/LLDP neighbour
        neighbour = ""
        if port.get('cdp') or port.get('lldp'):
            info = port.get('cdp') or port.get('lldp')
            neigh_dev = info.get('deviceId') or info.get('systemName', '')
            neigh_port = info.get('portId') or ''
            neighbour = f"{neigh_dev}:{neigh_port}" if neigh_dev else ""

        # Add data to records
        records.append({
            'timestamp': datetime.now(),
            'network': network_name,
            'device': device_name,
            'serial': serial,
            'port': port['portId'],#
            'enabled': port['enabled'],
            'status': port['status'],
            'speed': port.get('speed', ''),
            'duplex': port.get('duplex', ''),
            'recv_mbps': round(recv_mbps, 3),
            'sent_mbps': round(sent_mbps, 3),
            'total_mbps': round(total_mbps, 3),
            'errors': len(port.get('errors', [])),
            'discards': len(port.get('discards', [])),
            'neighbour': neighbour.strip()
        })

    time.sleep(0.15) # Pause for rate limit

# Create dataframe
df = pd.DataFrame(records)

print(f"Collected {len(df)} port samples from {df['serial'].nunique()} switches.")
print(df.head())

# Top 20 busiest ports
print("\nTop 20 busiest ports:")
print(df.nlargest(20, 'total_mbps')[['device', 'port', 'total_mbps', 'neighbour']])
