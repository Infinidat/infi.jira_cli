from infi.credentials_store import CLICredentialsStore
from logging import getLogger
import requests
from requests.auth import AuthBase, HTTPBasicAuth
import json


logger = getLogger(__name__)

PAT_PREFIX = "PAT:"


def is_pat(password):
    return password is not None and password.startswith(PAT_PREFIX)


def extract_pat(password):
    return password[len(PAT_PREFIX):]


class BasicOrBearerAuth(AuthBase):
    """
    requests-compatible auth object. Sends a Bearer token if the stored
    password is a PAT (PAT_PREFIX marker), otherwise falls back to Basic Auth.
    """

    def __init__(self, credentials):
        self.username = credentials.get_username()
        self.password = credentials.get_password()

    @property
    def is_token(self):
        return is_pat(self.password)

    @property
    def token(self):
        return extract_pat(self.password)

    def __call__(self, r):
        if self.is_token:
            r.headers['Authorization'] = 'Bearer {}'.format(self.token)
            return r
        return HTTPBasicAuth(self.username, self.password)(r)


class BasicAuthCredentialsStore(CLICredentialsStore):

    def __init__(self, auth_test_uri_template):
        super(CLICredentialsStore, self).__init__("jira")
        self._auth_test_uri_template = auth_test_uri_template

    def _get_file_folder(self):
        return ".infi.jira_cli"

    def authenticate(self, key, credentials):
        if credentials is None:
            return False
        password = credentials.get_password()
        uri = self._auth_test_uri_template.format(fqdn=self._fqdn)
        if is_pat(password):
            headers = {'Authorization': 'Bearer {}'.format(extract_pat(password))}
            response = requests.get(uri, headers=headers)
        else:
            auth = HTTPBasicAuth(credentials.get_username(), password)
            response = requests.get(uri, auth=auth)
        return response.status_code == 200


    def get_credentials(self, fqdn):
        self._fqdn = fqdn
        return super(BasicAuthCredentialsStore, self).get_credentials(fqdn)


class JIRACredentialsStore(BasicAuthCredentialsStore):

    def __init__(self):
        super(JIRACredentialsStore, self).__init__('https://{fqdn}/rest/api/2/project/')

    def ask_credentials_prompt(self, key):
        print(('\nConnecting to JIRA ' + str(key)))


class ConfluenceCredentialsStore(BasicAuthCredentialsStore):

    def __init__(self):
        super(ConfluenceCredentialsStore, self).__init__('https://{fqdn}/rest/prototype/1/search/site')

    def ask_credentials_prompt(self, key):
        print(('\nConnecting to Confluence ' + str(key)))
