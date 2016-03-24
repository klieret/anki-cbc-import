#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ConfigParser  # renamed to configparser in python3
import os.path
from .log import logger

config = ConfigParser.ConfigParser()

_config_files = ["cbcimport/config/default.config"]
_loaded = False  # were the _config_files at least loaded once


def _load_config(quiet=True):
    """ Load the configuration from _config_files.
    :param quiet: Write out logging messages?
    :return: None
    """
    logger.info("Loading configuration from the following file(s): %s." % ', '.join(_config_files))
    for cfile in _config_files:
        if not os.path.exists(cfile):
            if not quiet:
                logger.warning("Couldn't find config file {}".format(os.path.abspath(cfile)))
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
