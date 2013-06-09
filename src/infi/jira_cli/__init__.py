__import__("pkg_resources").declare_namespace(__name__)

from os import environ
from . import jissue, jish


def main():
    call_jish = int(environ.get("jish", "0"))
    return jish.main() if call_jish else jissue.main()
