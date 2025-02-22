import os
import logging
import meraki

def connect_to_meraki(print_console=False):

    dashboard = meraki.DashboardAPI(
        api_key=os.environ.get('MERAKI_API_KEY'),
        base_url='https://api.meraki.com/api/v1',
        print_console=False,
        output_log=True,
        inherit_logging_config=True,
        log_file_prefix=f'{__file__}'
    )
    return dashboard

def meraki_error(error):
    # Display error if returned by Meraki API
    message = f'Meraki API error: {error}\n' \
              f'\t- status code: {error.status}\n' \
              f'\t- reason: {error.reason}\n' \
              f'\t- message: {error.message}'
    return message


def other_error(error):
    # Display error if error returned for reason other that Meraki API
    message = f'Other error: {error}'
    return message


