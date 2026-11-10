import os
from pathlib import Path
import logging
import json
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

# Connect to the Dashboard
try:
    dashboard = meraki.DashboardAPI(api_key=os.environ.get('MERAKI_API_KEY'))
except meraki.APIError as e:
    logging.error(f"API error occured: {e}")
except Exception as e:
    logging.error(f"Unexpected error occured: {e}")

# Get organizations
try:
    organizations = dashboard.organizations.getOrganizations()
except meraki.APIError as e:
    logging.error(f"API error occured: {e}")
except Exception as e:
    logging.error(f"Unexpected error occured: {e}")

# Get all the networks
try:
    networks = dashboard.organizations.getOrganizationNetworks(organizationId=organizations[0]['id'])
except meraki.APIError as e:
    logging.error(f"API error occured: {e}")
except Exception as e:
    logging.error(f"Unexpected error occured: {e}")

# Filter out necessary networks
networks = [n for n in networks if 'Junior' in n['name']]

# Get firewall rules
try:
    rules = dashboard.appliance.getNetworkApplianceFirewallL3FirewallRules(networkId=networks[0]['id'])
except meraki.APIError as e:
    logging.error(f"API error occured: {e}")
except Exception as e:
    logging.error(f"Unexpected error occured: {e}")

# Get policy objects
try:
    policy_objects = dashboard.organizations.getOrganizationPolicyObjects(organizationId=organizations[0]['id'])
except meraki.APIError as e:
    logging.error(f"API error occured: {e}")
except Exception as e:
    logging.error(f"Unexpected error occured: {e}")

# Export firewall rules to JSON
backup_dir = Path('backup_json/l3_firewall_rules/')
backup_dir.mkdir(parents=True, exist_ok=True)
firewall_rules_file = backup_dir / 'js_l3_firewall_rules.json'
policy_objects_file = backup_dir / 'policy_objects.json'

with open(firewall_rules_file, 'w') as f:
    json.dump(rules, f, indent=4)

with open(policy_objects_file, 'w') as f:
    json.dump(policy_objects, f, indent=4)
