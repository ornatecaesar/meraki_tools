import meraki
from meraki_utils import connect_to_meraki, meraki_error, other_error
import os
from pathlib import Path

API_KEY = os.getenv('MERAKI_API_KEY')
LOG_PATH = Path('logs')

dashboard = connect_to_meraki(API_KEY)