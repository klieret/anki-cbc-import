#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Some small functions that don't have a place anywhere else or are used by several files.
"""


__author__ = "ch4noyu"
__email__ = "ch4noyu@yahoo.com"
__license__ = "LGPLv3"


def split_multiple_delims(string, delims):
    """ Like the string.split method, but with multiple delimeters, supplied as a list.
    :type string: str
    :type delims: list[str]"""
    # See http://stackoverflow.com/questions/4998629/python-split-string-with-multiple-delimiters
    string = unicode(string)
    for delim in delims:
        string = string.replace(delim, delims[0])
    return string.split(delims[0])


def layout_widgets(layout):
    """ Returns an iterable over the widgets of a layout.
    :type layout: A Q Layout
    :return:
    """
    return [layout.itemAt(i).widget() for i in range(layout.count())]
