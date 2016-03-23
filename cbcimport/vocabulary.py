#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Defines two classes:
- DataElement (contains all information about one word of vocabulary)
- DataSet (a class that bundles all DataElements)
"""

import csv
from log import logger
from .util import split_multiple_delims
from word import Word
from typing import List


class VocabularyCollection(object):
    """ Collects DataElements instances. """
    def __init__(self):
        self._data = []  # type: List[Word]
    
        # The index of the data element which is to be/was
        # imported to Anki.
        self._cursor = 0  # type: int
        self.dupes_in_queue = False  # type: bool
        self.added_in_queue = False  # type: bool
        self.blacklisted_in_queue = False  # type: bool

    def reverse(self):
        """ Reverses the order of all elements. """
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
        """
        :type element: Word
        :return:
        """
        if not self.dupes_in_queue and element.is_dupe:
            return False
        if not self.added_in_queue and element.is_added:
            return False
        if not self.blacklisted_in_queue and element.is_blacklisted:
            return False
        return True

    # todo: maybe make that a function that generates a VocabularyCollection object instead of a method
    def load(self, filename):
        """ Loads input file to self._data.
        :type filename: str
        """
        # todo: should be easily configurable
        # todo: should be easily overrideable
        logger.debug("Trying to load file '%s'." % filename)
        with open(filename,'r') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')
            
            # must match Anki fieldnames. If you want to ignore a field, just set it to ""
            field_names = ["Expression", "Kana", "Meaning", None]
    
            for row in reader:
                fields = [c.decode('utf8').strip() for c in row]
                logger.debug("Processing fields %s" % fields)
                element = Word()
                
                if not len(fields) == len(field_names):
                    raise (ValueError, "The number of supplied field_names (%d) doesn't match the number of "
                                       "fields in the file %s (%d)." % (len(field_names), filename, len(fields)))
                
                for i in range(len(fields)):
                    element[field_names[i]] = fields[i]

                # for tangorin:
                # if word doesn't contain any kanji, then the expression field will be empty 
                # and you have to take the kana field instead!
                # todo: Maybe implement that int element.set_fields_hook instead?
                if "Expression" in field_names and "Kana" in field_names:
                    logger.debug("Expression from Kana.")
                    if not element.expression:
                        element.expression(element["Kana"])

                self._data.append(element)
                logger.debug("Appended data element.")

    # =============== [ Statistics ] ===============

    def reduced_cursor(self):
        """ Returns the number of queue (!) elements with an index <= than the cursor.
        """
        ans = 0
        for i in range(self._cursor):
            if self.is_in_queue(self._data[i]):
                ans += 1
        return ans

    def count_data(self, boolean):
        """ Count all data entries with boolean(entry) == True
        :type boolean: fct
        """
        i = 0
        for entry in self._data:
            if boolean(entry):
                i += 1
        return i

    def len_all(self):
        """ Returns the number of all elements. """
        return self.count_data(lambda e: True)

    def len_added(self):
        """ Returns the number of all elements that were already added. """
        return self.count_data(lambda e: e.is_added)

    def len_dupe(self):
        """ Returns the number of all elements that were classified as duplicates. """
        return self.count_data(lambda e: e.is_dupe)
        
    def len_queue(self):
        """ Returns the number of all elements that are currently in the queue. """
        return self.count_data(lambda e: e.is_expression_in_queue)

    # =============== [ Return subsets ] ===============

    def get(self, boolean):
        """ Returns list with all elements with boolean(element) == True.
        :type boolean: Callable
        """
        ret = []
        for entry in self._data:
            if boolean(entry):
                ret.append(entry)
        return ret


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
        return self.get(lambda e: e.is_expression_in_queue)

    # =============== [ Navigate ] ===============

    # todo: should rather return the opposite!
    def go(self, func, start=None, dry=False, quiet=False):
        """ Updates self._cursor. 
        Starts with cursor = $start (default: func(self.cursor))
        and repeatedly calls cursor = func(cursor).
        Once the element at the cursor is an element that should be in
        the queue, we set self._cursor = cursor.
        Returns True if self._cursor remains unchanged and False otherwise.
        If dry == True, self._cursor remains untouched, and only the
        return value is given.
        :type func: function
        :type start: int
        :type dry: bool
        :type quiet: bool"""
        
        if not dry:
            print("Manipulating cursor.")

        old_cursor = self._cursor
        new_cursor = self._cursor

        print("old_cursor = new_cursor = {}".format(self._cursor))

        if start is None:
            # do NOT use "if not start", because start = 0 gets 
            # also evaluated as False.
            start = func(self._cursor)
        
        cursor = start
        print("start cursor = {}".format(start))

        while cursor in range(len(self._data)):
            print("trying cursor {}".format(cursor))
            if self.is_in_queue(self._data[cursor]):
                new_cursor = cursor
                print("In queue. Break!")
                break 
            else:
                if not quiet:
                    print("Skipping element %d" % cursor)
                cursor = func(cursor)
        
        if not dry:
            self._cursor = new_cursor

        if not dry and not quiet:
            print("Cursor is now %d" % self._cursor)
            print("Reduced cursor is now %d" % self.reduced_cursor())

        return new_cursor == old_cursor

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

    # =============== [ Booleans ] ===============

    def is_go_previous_possible(self):
        """ Can we go to the previous item, or are we already at the end of the
        queue?
        """
        return not self.go_previous(dry=True)

    def is_go_next_possible(self):
        """ Can we go to the next item, or are we already at the end of the
        queue?
        """
        return not self.go_next(dry=True)

    # todo: is this what we want?
    def is_queue_empty(self):
        """ Is the queue empty? Note: This also counts duplicates or already
        added elements, i.e. returns False if one of those is present in the queue.
        """
        return self.len_queue() == 0

    def is_expression_in_queue(self, exp):
        """ Is expression $exp already in the queue?
        :type exp: unicode string
        """
        # todo: make real thing
        if len(exp) >= 3:
            if exp in self.get_current().expression:
                return True
        else:
            delims = [',', ';', '・'.decode('utf-8')]
            exps = split_multiple_delims(self.get_current().expression, delims)
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