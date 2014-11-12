from infi.pyutils.lazy import cached_function


@cached_function
def get_confluence():
    from .config import Configuration
    from json_rest import JSONRestSender
    config = Configuration.from_file()
    client = JSONRestSender("http://{0}/rest/api".format(config.confluence_fqdn))
    client.set_basic_authorization(config.username, config.password)
    return client
