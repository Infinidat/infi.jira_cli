"""jadmin
infinidat jira admin command-line tool

Usage:
    jadmin custom-field update-dropdown-list <field-name> <values-filepath> [--sort-alphabetically]

Options:
    --help                       show this screen
"""

from .jissue import exception_handler


def _get_arguments(argv, environ):
    from .__version__ import __version__
    from docopt import docopt
    from munch import Munch
    arguments = Munch(docopt(__doc__, argv=argv, help=True, version=__version__))
    return arguments


def update_dropdown_list(field_name, values_filepath, sort_options_alphabetically):
    from .custom_field_editor import get_custom_field_id_by_name, update_custom_dropdown_field
    with open(values_filepath, 'rb') as fd:
        values = [item.strip() for item in fd.xreadlines()]
    field_id = get_custom_field_id_by_name(field_name)
    update_custom_dropdown_field(field_id, values, sort_options_alphabetically=sort_options_alphabetically)


@exception_handler
def _jadmin(argv, environ=dict()):
    from copy import deepcopy
    arguments = _get_arguments(argv, dict(deepcopy(environ)))
    if arguments['custom-field'] and ['update-dropdown-list']:
        update_dropdown_list(arguments['<field-name>'], arguments['<values-filepath>'], arguments['--sort-alphabetically'])


def main():
    from os import environ
    from sys import argv
    return _jadmin(argv[1:], environ)
