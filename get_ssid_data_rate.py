import os
import logging
from pathlib import Path
import pandas as pd
import meraki

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

# Variables
ssid_of_interest = 'SGW Devices'
ssid_data_rate_df = pd.DataFrame(columns=['start_time', 'end_time', 'download_kbps', 'upload_kbps', 'average_kbps'])

dashboard = meraki.DashboardAPI(api_key=os.getenv('MERAKI_API_KEY'),
                                print_console=False,
                                output_log=True,
                                inherit_logging_config=True,
                                log_file_prefix=f'{__file__}')

organization = dashboard.organizations.getOrganizations()[0]

networks = dashboard.organizations.getOrganizationNetworks(organizationId=organization['id'])

networks = [n for n in networks if 'wireless' in n['productTypes']]

for network in networks:
    ssids = dashboard.wireless.getNetworkWirelessSsids(networkId=network['id'])
    # ssids = [s for sublist in ssids for s in sublist if ssid_of_interest in s['name']]
    for ssid in ssids:
        if ssid_of_interest in ssid['name'] and ssid['enabled'] == True:
            ssid_usage = dashboard.wireless.getNetworkWirelessDataRateHistory(networkId=network['id'], timespan=86400, resolution=300,ssid=ssid['number'])
            # ssid_data_rate_df._append(
            #     {'start_time': ssid_usage['startTs']}
            # )
            print(ssid_data_rate_df.head())
