#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Sets up a logger 'logger' with 3 kinds of handlers:
* A handler for debugging that writes to the console.
* A handler for errors that whose messages will be caught by anki
* A handler for debugging that writes to a file.
The logger can either be used by importing the 'logger' symbol or by using
logging.getLogger('main_logger').
"""

import logging
import os.path
import sys

__author__ = "ch4noyu"
__email__ = "ch4noyu@yahoo.com"
__license__ = "LGPLv3"

logger = logging.getLogger('main_logger')
logger.setLevel(logging.DEBUG)

_formatter = logging.Formatter('cbcImport:%(levelname)s:%(message)s')

_sh_info = logging.StreamHandler(stream=sys.stdout)
_sh_info.setLevel(logging.DEBUG)
_sh_info.setFormatter(_formatter)

# will be caught by anki and displayed in a
# pop-up window
_sh_error = logging.StreamHandler(stream=sys.stderr)
_sh_error.setLevel(logging.ERROR)
_sh_error.setFormatter(_formatter)

_addon_dir = os.path.dirname(__file__)
_log_path = os.path.join(_addon_dir, 'ignore_dupes.log')
_fh = logging.FileHandler(_log_path, mode="w")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_formatter)

logger.addHandler(_fh)
logger.addHandler(_sh_error)
logger.addHandler(_sh_info)

logger.debug("Log will be saved at {}".format(os.path.abspath(_log_path)))
