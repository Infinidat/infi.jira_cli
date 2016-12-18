from os import path, getenv

CONFIGFILE_PATH_DEFAULT = path.expanduser(path.join("~", ".jissue"))


class ConfigurationError(Exception):
    pass


class Configuration(object):
    def __init__(self):
        self.jira_fqdn = ''
        self.confluence_fqdn = ''

    @classmethod
    def get_filepath(cls):
        return getenv("INFI_JIRA_CLI_CONFIG_PATH", CONFIGFILE_PATH_DEFAULT)

    @classmethod
    def from_file(cls):
        from json import load
        filepath = cls.get_filepath()
        if not path.exists(filepath):
            raise ConfigurationError("Configuration file does not exist, run 'jissue config set'")
        with open(filepath) as fd:
            data = load(fd)
        self = cls()
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self

    def serialize(self):
        return dict(jira_fqdn=self.jira_fqdn, confluence_fqdn=self.confluence_fqdn)

    def save(self):
        from json import dump
        filepath = self.get_filepath()
        with open(filepath, 'w') as fd:
            dump(self.serialize(), fd, indent=4)

    def to_json(self, indent=False):
        from json import dumps
        return dumps(self.serialize(), indent=indent)
