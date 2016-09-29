__import__("pkg_resources").declare_namespace(__name__)
from infi.pyutils.lazy import cached_function
from requests.auth import HTTPBasicAuth
from .config import Configuration


BASE_REST_URI = "https://{fqdn}/rest/"


@cached_function
def get_auth():
    config = Configuration.from_file()
    return HTTPBasicAuth(config.username, config.password)
