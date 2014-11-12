from schematics.models import Model
from schematics.types import StringType
from os import path

CONFIGFILE_PATH = path.expanduser(path.join("~", ".jissue"))


class ConfigurationError(Exception):
    pass


class Configuration(Model):
    jira_fqdn = StringType(required=True)
    confluence_fqdn = StringType(required=False)
    username = StringType(required=True)
    password = StringType(required=True)

    @classmethod
    def from_file(cls, filepath=None):
        from json import load
        if not path.exists(CONFIGFILE_PATH):
            raise ConfigurationError("Configuration file does not exist, run 'jissue config set'")
        filepath = filepath or CONFIGFILE_PATH
        with open(filepath) as fd:
            data = load(fd)
        self = cls()
        for key, value in data.iteritems():
            setattr(self, key, value)
        return self

    def save(self, filepath=None):
        from json import dump
        filepath = filepath or CONFIGFILE_PATH
        serialize = getattr(self, "to_python") if hasattr(self, "to_python") else getattr(self, "serialize")
        with open(filepath, 'w') as fd:
            dump(serialize(), fd, indent=4)

    def to_json(self, indent=False):
        from json import dumps
        serialize = getattr(self, "to_python") if hasattr(self, "to_python") else getattr(self, "serialize")
        return dumps(serialize(), indent=indent)
