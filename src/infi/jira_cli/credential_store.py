from infi.credentials_store import CLICredentialsStore
from logging import getLogger
import requests
from requests.auth import HTTPBasicAuth
import json


logger = getLogger(__name__)


class BasicAuthCredentialsStore(CLICredentialsStore):

    def __init__(self, auth_test_uri_template):
        super(CLICredentialsStore, self).__init__("jira")
        self._auth_test_uri_template = auth_test_uri_template

    def _get_file_folder(self):
        return ".infi.jira_cli"

    def authenticate(self, key, credentials):
        if credentials is None:
            return False
        auth = HTTPBasicAuth(credentials.get_username(), credentials.get_password())
        response = requests.get(self._auth_test_uri_template.format(fqdn=self._fqdn), auth=auth, verify=False)
        return response.status_code == 200


    def get_credentials(self, fqdn):
        self._fqdn = fqdn
        return super(BasicAuthCredentialsStore, self).get_credentials(fqdn)


class JIRACredentialsStore(BasicAuthCredentialsStore):

    def __init__(self):
        super(JIRACredentialsStore, self).__init__('https://{fqdn}/rest/api/2/issue/createmeta')

    def ask_credentials_prompt(self, key):
        print(('\nConnecting to JIRA ' + str(key)))


class ConfluenceCredentialsStore(BasicAuthCredentialsStore):

    def __init__(self):
        super(ConfluenceCredentialsStore, self).__init__('https://{fqdn}/rest/prototype/1/search/site')

    def ask_credentials_prompt(self, key):
        print(('\nConnecting to Confluence ' + str(key)))
