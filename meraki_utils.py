import meraki

def connect_to_meraki(api_key):

    dashboard = meraki.DashboardAPI(
        api_key=api_key,
        base_url='https://api.meraki.com/api/v1',
        print_console=False,
        output_log=False,
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


