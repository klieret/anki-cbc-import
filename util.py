#!/usr/bin/env python
# -*- coding: utf-8 -*-

def split_multiple_delims(string, delims):
    """ Like the string.split(...) method, but with 
    multiple delimeters. 
    See http://stackoverflow.com/questions/4998629/python-split-string-with-multiple-delimiters """
    # if not isinstance(string, str):
        # return string
    for delim in delims:
        string.replace(delim, delims[0])
    return string.split(delims[0])

def format_bool_html(value):
    """ HTML/CSS formatting for boolean/None values. """
    if value == False:
        fcolor = "White"
        bcolor = "Red"
    elif value == True:
        fcolor = "White"
        bcolor = "Green"
    else:
        fcolor = "Black"
        bcolor = "Yellow"
    return """<span style="background-color: %s; color: %s">%s</span>""" % (bcolor, fcolor, str(value))    