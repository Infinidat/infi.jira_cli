from infi.credentials_store import CLICredentialsStore
from logging import getLogger
from requests.auth import HTTPBasicAuth
import urlparse
import json

logger = getLogger(__name__)

AUTH_TEST_URI = '/rest/api/2/issue/createmeta'

class JiraCLICredentialStore(CLICredentialsStore):

    def __init__(self):
        super(CLICredentialsStore, self).__init__("jissue")

    def _get_file_folder(self):
        return ".infinidat"

    def authenticate(self, key, credentials):
        auth = HTTPBasicAuth(credentials.get_username(), credentials.get_password())
        try:
            response = requests.get(urlparse.join(BASE_REST_URI.format(self._fqdn), AUTH_TEST_URI),
                                    auth=auth)
            response.raise_for_error()
            content = json.loads(respone.content)
            return len(content['projects']) > 0
        except:
            return False

    def ask_credentials_prompt(self, key):
        print '\nConnecting to JIRA ' + str(key)

    def get_credentials(self, fqdn):
        self._fqdn = fqdn
        return super(JiraCLICredentialStore, self).get_credentials(fqdn)