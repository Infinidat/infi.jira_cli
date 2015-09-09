from json_rest import JSONRestSender
from infi.pyutils.lazy import cached_function


ADD_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}"
GET_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoptions/{customfield_id}"
REORDER_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}/{option_id}/move"
DELETE_URI = "/jiracustomfieldeditorplugin/1.1/user/customfieldoption/{customfield_id}/{option_id}"


@cached_function
def get_api():
    from .config import Configuration
    from jira import JIRA
    config = Configuration.from_file()
    api = JSONRestSender("https://%s/rest" % config.jira_fqdn)
    api.set_basic_authorization(config.username, config.password)
    return api


def get_fields():
    return get_api().get("/api/2/field")


def get_custom_field_id_by_name(name):
    [custom_field] = [custom_field for custom_field in get_fields() if
                      custom_field["name"] == name]
    return custom_field['id']


def get_options_for_custom_field(field_id):
    return get_api().get(GET_URI.format(customfield_id=field_id))


def update_custom_dropdown_field(field_id, values, sort_options_alphabetically=True):
    options = get_options_for_custom_field(field_id)

    field_options = {item['optionvalue']: item for item in options}
    # we shouldn't delete old values, as existing issues can use them
    new_values = set(value for value in values if value not in field_options.keys())

    for value in new_values:
        data = dict(disabled=False, optionvalue=value)
        new_option = get_api().post(ADD_URI.format(customfield_id=field_id), data=data)
        field_options[value] = new_option

    if sort_options_alphabetically:
        sort_custom_dropdown_field(field_id, field_options.values())


def sort_custom_dropdown_field(field_id, values):
    sorted_options = sorted(values, key=lambda item: item['optionvalue'], reverse=True)
    for option in sorted_options:
        uri = REORDER_URI.format(customfield_id=field_id, option_id=option['id'])
        get_api().post(uri, data=dict(position="First"))


def wipe_all_options_in_custom_dropdown_field(field_id):
    options = get_options_for_custom_field(field_id)
    for option in options:
        uri = DELETE_URI.format(customfield_id=field_id, option_id=option['id'])
        get_api().delete(uri)


