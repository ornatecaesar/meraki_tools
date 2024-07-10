# remove_vlan_from_trunks.py

"""
Removes the specified VLAN from the Routing & DHCP configuration of Switches,
then removes the specified VLAN from all trunks that have the VLAN in the
Allowed VLANs list
"""

import os
from pathlib import Path
import logging

API_KEY = os.environ.get('MERAKI_API_KEY')

# Configure logging directory
logging_dir = Path('logs')
if not logging_dir.exists():
    logging_dir.mkdir(parents=True)

# Configure logging filename, level and content
script_name = os.path.basename(__file__)
script_name = os.path.splitext(script_name)[0]
log_file_name = f'{script_name}.log'
logging.basicConfig(filename=f'logs/{log_file_name}',
                    level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%d/%m/%Y %I:%M:%S %p')
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger('meraki').setLevel(logging.WARNING)


