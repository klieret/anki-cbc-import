#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Defines the class VocabularyCollection which is a collection of instances of the 'Word'
class. It also implements the 'queue'.
"""


import csv
from log import logger
from .util import split_multiple_delims
from word import Word
from typing import List
from config import config

__author__ = "ch4noyu"
__email__ = "ch4noyu@yahoo.com"
__license__ = "LGPLv3"


class VocabularyCollection(object):
    """ A Collection of instances of the 'Word' class.
    * Most important term: 'queue': When the user clicks the <<, <, >, >> buttons, i.e. wants
      to move from one entry (Word instance) to another, he might want to skip the entries that
      were duplicates, were blacklisted or were already added. Thus this implements something
      lik a queue that skips those entries if configured to do so.
      However this is not implemented as a list VocabularyCollection.queue, but rather we define
      functions to go through the whole dataset VocabularyCollection._data (of type List[Word]
      and mimic such a behaviour.
    * Calling functions like VocabularyCollection.next, previous etc. changes VocabularyCollection._cursor,
      the entry at the cursor can then be retrieved with VocabularyCollection.get_current.
    * Note that to check if an element is a duplicate, blacklisted etc., the method of the element
      i.e. of the Word class is used, whereas to check if its in the queue, we use
      VocabularyCollection.is_in_queue (this allows to customize which elements are being skipped
      in the queue)."""
    
    # ========================= [ Basics ] =========================
    
    def __init__(self):
        self._data = []  # type: List[Word]
    
        # The index of the data element which is to be/was
        # imported to Anki, i.e. the element we are 'looking at' right now.
        self._cursor = 0  # type: int

        # Which entries should be skipped in the 'queue'.
        self.dupes_in_queue = False  # type: bool
        self.added_in_queue = False  # type: bool
        self.blacklisted_in_queue = False  # type: bool
        self.rest_in_queue = True  # type: bool

        self.scan_for_duplicates = config.getboolean("general", "scan_for_duplicates")  # type: bool

    def reverse(self):
        """ Reverses the order of all elements.
        Note: This actually reverses self._data and is not just some play on the
        behaviour on the VocabularyCollection.next, previous, etc. functions. """
        self._data.reverse()
        self._cursor = len(self._data) - 1 - self._cursor

    def get_current(self):
        """ Return the element at the cursor. """
        return self._data[self._cursor]

    def set_current(self, elem):
        """ Replace the element at the cursor with $elem.
        :type elem: Word
        """
        self._data[self._cursor] = elem 

    def is_in_queue(self, element):
        """ This basically implements the 'queue'. Depending on the settings,
        skips duplicate, already added and blacklisted words.
        :type element: Word
        :return:True if element is in queue, False otherwise.
        """
        if not self.dupes_in_queue and element.is_dupe:
            return False
        if not self.added_in_queue and element.is_added:
            return False
        if not self.blacklisted_in_queue and element.is_blacklisted:
            return False
        if not self.rest_in_queue and element.is_rest:
            return False
        return True

    # ========================= [ Load ] =========================

    # todo: maybe make that a function that generates a VocabularyCollection object instead of a method
    def load(self, filename):
        """ Loads input file to self._data.
        :type filename: str
        """
        # todo: should be easily configurable
        logger.debug("Trying to load file '%s'." % filename)
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')
            
            # must match Anki fieldnames. If you want to ignore a field, just set it to ""
            field_names = ["Expression", "Kana", "Meaning", None]
    
            for row in reader:
                fields = [c.decode('utf8').strip() for c in row]
                element = Word()
                
                if not len(fields) == len(field_names):
                    raise (ValueError, "The number of supplied field_names (%d) doesn't match the number of "
                                       "fields in the file %s (%d)." % (len(field_names), filename, len(fields)))
                
                for i in range(len(fields)):
                    element[field_names[i]] = fields[i]

                if self.scan_for_duplicates:
                    element.check_duplicate()

                self._data.append(element)

    # ========================= [ Statistics ] =========================

    def full_cursor(self):
        return self._cursor

    def reduced_cursor(self, cursor=None):
        """ Returns the number of queue (!) elements with an index <= than the cursor.
        :param cursor: Int. Defaults to self._cursor. ValueError if out of range.
        :type cursor: int
        """
        if cursor is None:
            cursor = self._cursor
        return sum(self.is_in_queue(self._data[i]) for i in range(cursor))

    def _count_data(self, bool_fct):
        """ Sums over all bool_fct(entry). If bool_fct always returns True/False
        this returns the number of entries with bool_fct(entry) == True.
        :type bool_fct: Function that returns a bool.
        """
        return sum(bool_fct(entry) for entry in self._data)

    def len_all(self):
        """ Returns the total number of all elements. """
        return self._count_data(lambda e: True)

    def len_added(self):
        """ Returns the number of all elements that were already added. """
        return self._count_data(lambda e: e.is_added)

    def len_dupe(self):
        """ Returns the number of all elements that were classified as duplicates. """
        return self._count_data(lambda e: e.is_dupe)

    def len_black(self):
        """ Returns the number of all elements that were blacklisted. """
        return self._count_data(lambda e: e.is_blacklisted)
        
    def len_queue(self):
        """ Returns the number of all elements that are currently in the queue. """
        return self._count_data(lambda e: self.is_in_queue(e))
        # alternative implementation: use self.reduced_cursor

    # ========================= [ Return subsets ] =========================

    def get(self, boolean_fct):
        """ Returns list with all elements with boolean_fct(element) == True.
        :type boolean_fct: Callable
        """
        return [entry for entry in self._data if boolean_fct(entry)]

    def get_all(self):
        """ Returns list of all elements. """
        return self.get(lambda e: True)

    def get_added(self):
        """ Returns list of all elements that were already added. """
        return self.get(lambda e: e.is_added)

    def get_dupe(self):
        """ Returns list of all elements that were classified as duplicates. """
        return self.get(lambda e: e.is_dupe)
        
    def get_queue(self):
        """ Returns list of all elements that are currently in the queue. """
        return self.get(lambda e: self.is_in_queue(e))

    # ========================= [ Navigation ] =========================

    def go(self, func, start=None, dry=False, quiet=True):
        """ Updates self._cursor. 
        Starts with cursor = $start (default: func(self.cursor)) and repeatedly calls
        cursor = func(cursor).
        Once the element at the cursor is an element in the queue, we set self._cursor = cursor.
        Returns False if self._cursor remains unchanged and True otherwise.
        If dry == True, self._cursor remains untouched, and only the
        return value is given (Useful if we want to test if we are at the
        end of the queue etc.)
        :type func: function
        :type start: int
        :type dry: bool
        :param quiet: Set to False for debugging.
        :type quiet: bool"""

        def qprint(string):
            if not quiet:
                print string
            else:
                return

        old_cursor = self._cursor
        new_cursor = self._cursor
        qprint("old_cursor = {}".format(self._cursor))

        if start is None:
            # do NOT use "if not start", because start = 0 gets 
            # also evaluated as False.
            start = func(self._cursor)
        
        cursor = start
        qprint("start cursor = {}".format(start))

        while cursor in range(len(self._data)):
            qprint("trying cursor {}".format(cursor))
            if self.is_in_queue(self._data[cursor]):
                new_cursor = cursor
                qprint("In queue. Break!")
                break 
            else:
                qprint("Skipping.")
                cursor = func(cursor)
        
        if not dry:
            self._cursor = new_cursor
            qprint("Cursor is now %d" % self._cursor)
            qprint("Reduced cursor is now %d" % self.reduced_cursor())

        return new_cursor != old_cursor

    def go_next(self, dry=False):
        """ Go to next queue element 
        (i.e. sets self._cursor to the index of the next queue element)
        Returns False if we are already at the last queue element.
        If dry == True: self._cursor remains untouched, only the
        return value is given.
        :type dry: bool
        """
        return self.go(lambda x: x+1, dry=dry)

    def go_previous(self, dry=False):
        """ Go to previous queue element 
        (i.e. sets self._cursor to the index of the previous queue element)
        Returns False if we are already at the first queue element.
        If dry == True: self._cursor remains untouched, only the
        return value is returned.
        :type dry: bool
        """
        return self.go(lambda x: x-1, dry=dry)

    def go_first(self):
        """ Go to first queue element 
        (i.e. sets self._cursor to the index of the first queue element)
        Returns False if we are already at the first queue element.
        """
        return self.go(lambda x: x+1, start=0)
        
    def go_last(self):
        """ Go to last queue element 
        (i.e. sets self._cursor to the index of the last queue element)
        Returns False if we are already at the last queue element.
        """
        return self.go(lambda x: x-1, start=len(self._data)-1)

    # ========================= [ Booleans ] =========================

    def is_go_previous_possible(self):
        """ Can we go to the previous item, or are we already at the end of the
        queue?
        """
        return self.go_previous(dry=True)

    def is_go_next_possible(self):
        """ Can we go to the next item, or are we already at the end of the queue? """
        return self.go_next(dry=True)

    def is_empty(self):
        return self.len_all() == 0

    def is_queue_empty(self):
        """ Is the queue empty? """
        return self.len_queue() == 0

    def is_expression_in_queue(self, exp):
        """ Is expression $exp already in the queue?
        :type exp: unicode string
        """
        # todo: docstring about how this is used
        if len(exp) >= 3:
            if exp in self.get_current()["Expression"]:
                return True
        else:
            delims = [',', ';', '・'.decode('utf-8')]
            exps = split_multiple_delims(self.get_current()["Expression"], delims)
            if exp in exps:
                return True
        return False
            

if __name__ == "__main__":
    # for testing purposes.
    # added trailing underscore for some variables
    # to avoid name shaddowing
    import os.path
    ds = VocabularyCollection()
    filename_ = "tan.csv"
    if os.path.exists(filename_):
        ds.load(filename_)
        # set some duplicated events.
        for i_ in [1, 2, 5]:
            ds._cursor = i_
            element_ = ds.get_current()
            element_.is_dupe = True
            ds.set_current(element_)
        ds.go_first()
    else:
        print("Test file %s not found." % filename_)
