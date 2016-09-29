from infi.pyutils.lazy import cached_function
from .rest import BASE_REST_URI, get_auth
from .config import Configuration
import requests
import urlparse


FIELD_URI = "/api/2/field"
ADD_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}"
GET_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoptions/{customfield_id}"
REORDER_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}/{option_id}/move"
DELETE_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}/{option_id}"


@cached_function
def get_jira_url(endppoint, *args, **kwargs):
    config = Configuration.from_file()
    return urlparse.join(BASE_REST_URI.format(fqdn=config.jira_fqdn), endpoint)


def get_fields():
    return requests.get(get_jira_url(FIELD_URI), auth=get_auth()).json()


def get_custom_field_id_by_name(name):
    [custom_field] = [custom_field for custom_field in get_fields() if
                      custom_field["name"] == name]
    return custom_field['id']


def get_options_for_custom_field(field_id):
    return requests.get(get_jira_url(GET_URI.format(customfield_id=field_id)), auth=get_auth()).json()


def update_custom_dropdown_field(field_id, values, sort_options_alphabetically=True):
    options = get_options_for_custom_field(field_id)

    field_options = {item['optionvalue']: item for item in options}
    # we shouldn't delete old values, as existing issues can use them
    new_values = set(value for value in values if value not in field_options.keys())

    for value in new_values:
        data = dict(disabled=False, optionvalue=value)
        new_option = requests.post(get_jira_url(ADD_URI.format(customfield_id=field_id)),
                                   auth=get_auth(),
                                   data=data).json()
        field_options[value] = new_option

    if sort_options_alphabetically:
        sort_custom_dropdown_field(field_id, field_options.values())


def sort_custom_dropdown_field(field_id, values):
    sorted_options = sorted(values, key=lambda item: item['optionvalue'], reverse=True)
    for option in sorted_options:
        uri = get_jira_url(REORDER_URI.format(customfield_id=field_id, option_id=option['id']))
        requests.post(uri, auth=get_auth(), data=dict(position="First"))


def wipe_all_options_in_custom_dropdown_field(field_id):
    options = get_options_for_custom_field(field_id)
    for option in options:
        uri = DELETE_URI.format(customfield_id=field_id, option_id=option['id'])
        uri = get_jira_url(DELETE_URI.format(customfield_id=field_id, option_id=option['id'])
        requests.delete(uri, auth=get_auth())
