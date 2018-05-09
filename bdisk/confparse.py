import validators
from urllib.parse import urlparse
try:
    from lxml import etree
    has_lxml = True
except ImportError:
    import xml.etree.ElementTree as etree
    has_lxml = False

"""Read a configuration file, parse it, and make it available to the rest of
BDisk."""

class Conf(object):
    def __init__(self, cfg, profile = None, id_type = 'name'):
        """Conf classes accept the following parameters:
        cfg - The configuration. Can be a filesystem path, a string, bytes,
              or a stream

        profile (optional) - A sub-profile in the configuration. If None is
                             provided, we'll first look for a profile named
                             'default'. If one isn't found, then the first
                             profile found will be used
        id_type (optional) - The type of identifer to use for profile=.
                             Valid values are:

                                id
                                name
                                uuid"""
        pass
