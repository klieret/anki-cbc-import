#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Reads configuration files. The result is stored in the ConfigParser instance 'logger'.
Note that importing this module will automatically load the configuration files, so there
is no need to call load_config by yourself. If you want to reaload the config file, please
use reload_config(), as load_config is designed check if the configuration files were already
loaded and if yes, won't do anything.
"""

import ConfigParser
import os.path
from .log import logger

__author__ = "ch4noyu"
__email__ = "ch4noyu@yahoo.com"
__license__ = "LGPLv3"


# Note: The ConfigParser module was renamed to configparser in python3
#       and you can't access stuff via ConfigParser[...][...] in python2.
#       use ConfigParser.get(..., ...) instead.

config = ConfigParser.ConfigParser()

_config_files = [os.path.join(os.path.dirname(__file__), "config/default.config")]
_loaded = False  # were the _config_files at least loaded once


def _load_config(quiet=True):
    """ Load the configuration from _config_files.
    :param quiet: Write out logging messages?
    :return: None
    """
    logger.info("Loading configuration from the following file(s): %s." %
                ', '.join([os.path.abspath(f) for f in _config_files]))
    for cfile in _config_files:
        if not os.path.exists(cfile):
            if not quiet:
                logger.warning("Couldn't find config file {}".format(os.path.abspath(cfile)))
        else:
            config.read(cfile)
    global _loaded
    _loaded = True


def load_config(quiet=False):
    """ Load the configuration files but only if they were not already loaded before.
    :param quiet: Write out logging messages?
    :return: Did we have to load the configuration files?
    """
    if not _loaded:
        _load_config(quiet=quiet)
        return True
    else:
        return False


def reload_config(quiet=True):
    """ Load the configuration.
    :param quiet: Write out logging messages?
    :return: None
    """
    _load_config(quiet=quiet)


# make sure that the configuration is loaded if this module is imported
load_config()
