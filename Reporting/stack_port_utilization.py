#! /usr/bin/env python3
"""
Meraki Switch Port Utilization Report Generator
-----------------------------------------------
Generates per-switch bar charts of the maximum port bandwidth utilization (Mbps)
over the specified lookback period and saves them to a single PDF report.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from meraki import DashboardAPI

from meraki_utils import connect_to_meraki, meraki_error

# ------------------------------
# Configuration
# ------------------------------

CONFIG = {
    'lookback_days': 30,
    'interval_seconds': 14400, # 4 hours
    'dpi': 150,
    'figure_size': (18, 6),
    'report_prefix': 'switch_port_utilization',
    'log_level': logging.INFO
}

# ------------------------------
# Setup logging
# ------------------------------

logging.basicConfig(
    level=CONFIG['log_level'],
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_all_switch_mac(dashboard: DashboardAPI, ord_id: str) -> List[str]:
    """Collect MAC addresses of all switch devices across all networks"""
    networks = dashboard.organizations.getOrganizationNetworks(ord_id, productTypes=['switch'])

    macs = []
    for network in networks:
        try:
            stacks = dashboard.switch.getNetworkSwitchStacks(network['id'])
            for stack in stacks:
                for member in stack.get('members', []):
                    macs.append(member['mac'])
        except Exception as e:
            logger.warning(f"Failed to get stacks fr networrk {network['id']}: {e}")

    logger.info(f"Found {len(macs)} switch MAC addresses")
    return macs


def fetch_port_usage_history(dashboard: DashboardAPI, org_id: str, macs: List[str]) -> Dict:
    """Fetch historical port usage data for all switches."""
    try:
        data = dashboard.switch.getOrganizationSwitchPortsUsageHistoryByDeviceByInterval(
            organizationId=org_id,
            macs=macs,
            timespan=int(timedelta(days=CONFIG['lookback_days']).total_seconds()),
            interval=CONFIG['interval_seconds'],
            total_pages='all'
        )
        logger.info(f"Fetched usage history for {len(data.get('items', []))} switches")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch port usage history: {e}")
        raise


def create_utilization_figure(item: Dict) -> Tuple[plt.Figure, str]:
    """Generate bar chart figure for a single switch"""
    switch_name = item['name']
    ports = item['ports']

    rows = []
    for port in ports:
        port_id = port['portId']
        for interval in port['intervals']:
            bw = interval.get('bandwidth', {}).get('usage', {})
            rows.append({
                'portId': port_id,
                'bw_total_mbps': bw.get('total', 0.0) / 1000
            })

    if not rows:
        logger.info(f"No usage data for switch {switch_name}")
        return None, switch_name

    df = pd.DataFrame(rows)
    util = df.groupby('portId')['bw_total_mbps'].max().reset_index()
    order = sorted(util['portId'], key=int)

    fig, ax = plt.subplots(figsize=CONFIG['figure_size'])
    sns.barplot(
        data=util,
        x='portId',
        y='bw_total_mbps',
        order=order,
        ax=ax
    )

    ax.bar_label(ax.containers[0], fmt='%.1f')
    ax.set_title(
        f"Maximum Port Utilization (Mbps) - {switch_name}\n"
        f"Period: last {CONFIG[f'lookback_days']} days up to {datetime.now().strftime('%d-%m-%Y')}"
    )

    ax.set_ylabel("Max Bandwidth (Mbps)")
    ax.set_xlabel("Port ID")

    return fig, switch_name


def main():
    dashboard: DashboardAPI = connect_to_meraki(os.environ.get('MERAKI_API_KEY'))
    org_id = dashboard.organizations.getOrganizations()[0]['id']

    macs = get_all_switch_mac(dashboard, org_id)
    if not macs:
        logger.error("No switches found")
        return

    switches_data = fetch_port_usage_history(dashboard, org_id, macs)

    # Sort switches alphabetically
    switches_data['items'] = sorted(
        switches_data['items'],
        key=lambda x: x['name'].lower()
    )

    figures = []
    for item in switches_data['items']:
        fig, name = create_utilization_figure(item)
        if fig is not None:
            figures.append((fig, name))

    if not figures:
        logger.error("No figures generated")
        return

    # Generate dated filename
    today = datetime.now().strftime('%Y-%m-%d')
    pdf_path = f"{CONFIG['report_prefix']}_{today}_lookback-{CONFIG['lookback_days']}_days.pdf"

    with PdfPages(pdf_path) as pdf:
        for fig, name in figures:
            pdf.savefig(fig, dpi=CONFIG['dpi'], bbox_inches='tight')
            plt.close(fig)

    logger.info(f"Report saved: {pdf_path} ({len(figures)} pages)")


if __name__ == '__main__':
    main()
