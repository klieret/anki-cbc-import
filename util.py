#!/usr/bin/env python
# -*- coding: utf-8 -*-

def split_multiple_delims(string, delims):
    """ Like the string.split(...) method, but with 
    multiple delimeters. 
    See http://stackoverflow.com/questions/4998629/python-split-string-with-multiple-delimiters """
    for delim in delims:
        expression.replace(delim, delims[0])
    return string.split(delims[0])