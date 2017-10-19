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


# Note 1:  The ConfigParser module was renamed to configparser in python3
#          and you can't access stuff via ConfigParser[...][...] in python2.
#          use ConfigParser.get(..., ...) instead.
# Note 2:  SaveConfigParser: Derived class of ConfigParser that implements a more-sane variant of the magical
#          interpolation feature. This implementation is more predictable as well. New applications should prefer this
#          version if they don’t need to be compatible with older versions of Python.

config = ConfigParser.SafeConfigParser()

# The 'default' configuration and also the fallback configuration, if we can't retrieve a value
# from _save_config_file
_backup_config_files = [os.path.join(os.path.dirname(__file__), "config", "_default", "_default.txt")]

# Save the configuration here. Gets opened after the _backup_config_files and thus will overwrite
# values from keys that are present in both files.
_save_config_file = os.path.join(os.path.dirname(__file__), "config", "saved.txt")

# were the config files loaded at least loaded once?
_loaded = False


def _load_config(quiet=True):
    """ Load the configuration from _backup_config_files.
    :param quiet: Write out logging messages?
    :return: None
    """
    all_config_files = _backup_config_files + [_save_config_file]
    logger.info("Loading configuration from the following file(s): %s." %
                ', '.join([os.path.abspath(f) for f in all_config_files]))
    for cfile in all_config_files:
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


def write_config(quiet=True):
    """ Write the configuration back to the non-backup config file.
    :param quiet: Write out logging messages?
    :return: None
    """
    with open(_save_config_file, 'wb') as cfile:
        config.write(cfile)
    if not quiet:
        logger.debug("Saved configuration at {}".format(os.path.abspath(_save_config_file)))


# For convenience: add the write/reload method to the config object:
config.reload_config = reload_config
config.write_config = write_config

# make sure that the configuration is loaded if this module is imported
load_config()
