import requests
import logging

logger = logging.getLogger(__name__)


class Plugin(object):
    def __init__(self, plugin_data):
        self._plugin_data = plugin_data
        self._name = self._plugin_data['name']
        self._key = self._plugin_data['key']
        self._installed_version = self._plugin_data['version']

    def get_info(self):
        return get("{}".format(self._plugin_data['links']['self']))

    def get(self, uri):
        return get("{}/{}".format(self._plugin_data['links']['self'], uri))

    def get_license_data(self):
        try:
            return self.get("license")
        except requests.HTTPError as error:
            logger.warn(error)
        return dict()

    def get_summary(self):
        return self.get("summary")

    @property
    def key(self):
        return self._key

    @property
    def installed_version(self):
        return self._installed_version

    @property
    def name(self):
        return self._name

    def get_info_on_marketplace(self):
        try:
            return get(self._plugin_data['links']['self'].replace("plugins/1.0/", "plugins/1.0/available/"))
        except requests.HTTPError as error:
            logger.warn(error)
        return dict()

    @property
    def marketplace_version(self):
        return self.get_info_on_marketplace().get('version')

    def __repr__(self):
        return "<Plugin: {}, v{}>".format(self._name, self._installed_version)

    @property
    def type(self):
        return 'User' if self._plugin_data['userInstalled'] else 'System'

    def is_enabled(self):
        return self._plugin_data['enabled']

    def is_update_available(self):
        return self.marketplace_version and self.marketplace_version != self.installed_version

    @property
    def expires_in(self):
        from datetime import datetime
        if not self.license_details.end_date:
            return False
        return (self.license_details.end_date - datetime.now()).days

    def is_license_expires_soon(self, days=60):
        if not self.expires_in:
            return False
        return self.expires_in <= days

    @property
    def license_details(self):
        from dateutil.parser import parse
        from munch import Munch
        license_data = self.get_license_data()
        return Munch(type=license_data.get('licenseType', '').lower(),
                     evaluation=license_data.get('evaluation'),
                     start_date=parse(license_data['creationDateString']) if license_data.get('creationDateString') else None,
                     end_date=parse(license_data['maintenanceExpiryDateString']) if license_data.get('maintenanceExpiryDateString') else None,
                     contract_number=license_data.get('supportEntitlementNumber'),
                     valid=license_data.get('valid'))


def get(uri, *args, **kwargs):
    from infi.jira_cli.jira_adapter import get_jira
    jira = get_jira()
    respnose = requests.get("{}{}".format(jira._options['server'], uri), auth=requests.auth.HTTPBasicAuth(*jira._session.auth))
    respnose.raise_for_status()
    return respnose.json()


def get_plugins():
    return [Plugin(item) for item in get("/rest/plugins/1.0/")['plugins']]

def get_available_upgrades():
    return get("/rest/plugins/1.0/available/upgrades")
