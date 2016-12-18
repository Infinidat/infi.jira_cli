from infi.pyutils.lazy import cached_function
from .config import Configuration
import requests
try:
    from urlparse import urljoin
except:
    from urllib.parse import urljoin


BASE_REST_URI = "https://{fqdn}/rest/"
FIELD_URI = "/api/2/field"
ADD_URI = "jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}"
GET_URI = "jiracustomfieldeditorplugin/1.1/user/customfieldoptions/{customfield_id}"
REORDER_URI = "jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}/{option_id}/move"
DELETE_URI = "jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}/{option_id}"




@cached_function
def get_auth(fqdn):
    config = Configuration.from_file()
    credential_store = ConfluenceCredentialsStore()
    credentials = credential_store.get_credentials(fqdn)
    return HTTPBasicAuth(credentials.get_username(), credentials.get_password())


@cached_function
def get_headers():
    return {'Accept': 'application/json'}


@cached_function
def get_jira_url(endpoint, *args, **kwargs):
    config = Configuration.from_file()
    return urljoin(BASE_REST_URI.format(fqdn=config.jira_fqdn), endpoint)


def get_fields():
    config = Configuration.from_file()
    return requests.get(get_jira_url(FIELD_URI),
                        auth=get_auth(config.jira_fqdn),
                        headers=get_headers()).json()


def get_custom_field_id_by_name(name):
    [custom_field] = [custom_field for custom_field in get_fields() if
                      custom_field["name"] == name]
    return custom_field['id']


def get_options_for_custom_field(field_id):
    return requests.get(get_jira_url(GET_URI.format(customfield_id=field_id)),
                        auth=get_auth(config.jira_fqdn),
                        headers=get_headers()).json()


def update_custom_dropdown_field(field_id, values, sort_options_alphabetically=True):
    options = get_options_for_custom_field(field_id)

    field_options = {item['optionvalue']: item for item in options}
    # we shouldn't delete old values, as existing issues can use them
    new_values = set(value for value in values if value not in list(field_options.keys()))
    config = Configuration.from_file()

    for value in new_values:
        data = dict(disabled=False, optionvalue=value)
        new_option = requests.post(get_jira_url(ADD_URI.format(customfield_id=field_id)),
                                   auth=get_auth(config.jira_fqdn),
                                   data=data).json()
        field_options[value] = new_option

    if sort_options_alphabetically:
        sort_custom_dropdown_field(field_id, list(field_options.values()))


def sort_custom_dropdown_field(field_id, values):
    sorted_options = sorted(values, key=lambda item: item['optionvalue'], reverse=True)
    config = Configuration.from_file()
    for option in sorted_options:
        uri = get_jira_url(REORDER_URI.format(customfield_id=field_id, option_id=option['id']))
        requests.post(uri, auth=get_auth(config.jira_fqdn), data=dict(position="First"))


def wipe_all_options_in_custom_dropdown_field(field_id):
    options = get_options_for_custom_field(field_id)
    config = Configuration.from_file()
    for option in options:
        uri = get_jira_url(DELETE_URI.format(customfield_id=field_id, option_id=option['id']))
        requests.delete(uri, auth=get_auth(config.jira_fqdn))
