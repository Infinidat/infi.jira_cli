from schematics.models import Model
from schematics.types import StringType
from os import path

CONFIGFILE_PATH = path.expanduser(path.join("~", ".jissue"))


class Configuration(Model):
    fqdn = StringType(required=True)
    username = StringType(required=True)
    password = StringType(required=True)

    @classmethod
    def from_file(cls, filepath=None):
        from json import load
        filepath = filepath or CONFIGFILE_PATH
        with open(filepath) as fd:
            return cls(**load(fd))

    def save(self, filepath=None):
        from json import dump
        filepath = filepath or CONFIGFILE_PATH
        with open(filepath, 'w') as fd:
            dump(self.to_python(), fd, indent=4)

    def to_json(self, indent=False):
        from json import dumps
        return dumps(self.to_python(), indent=indent)
