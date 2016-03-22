#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Defines two classes:
- DataElement (contains all information about one word of vocabulary)
- DataSet (a class that bundles all DataElements)
"""

import csv
from log import logger
from util import split_multiple_delims


class DataElement(object):
    """ Contains all information about one word of vocabulary. """
    
    def __init__(self):
        # The fields that are to be synchronized with 
        # the anki note. 
        # Should be of type 
        # {"fieldname":"value", ...}
        self._fields = {}

        self._dupe = False
        self._added = False

    # ---------- Getters & Setters ---------------

    def get_field(self, key):
        return self._fields[key]

    def set_field(self, key, value):
        self._fields[key] = value
        self.set_fields_hook()

    def get_expression(self):
        return self.get_field("Expression")

    def set_expression(self, value):
        return self.set_field("Expression", value)

    def is_dupe(self):
        return self._dupe

    def set_dupe(self, boolean):
        self._dupe = boolean

    def is_added(self):
        return self._added

    def set_added(self, bool):
        self._added = bool

    # ----------------------------------------        

    def is_in_queue(self):
        """ Should this element pop up in the current queue 
        of vocabulary that we want to add? """

        return not self.is_dupe() and not self.is_added()

    def set_fields_hook(self):
        """ Should be run after changes to self._fields were
        made. """              
        pass


class DataSet(object):
    """ Collects DataElements instances. """

    def __init__(self):
        self._data = []
    
        # The index of the data element which is to be/was
        # imported to Anki.
        self._cursor = 0

    def reverse(self):
        """ Reverses the order of all elements. """
        self._data.reverse()
        self._cursor = len(self._data) - 1 - self._cursor

    def get_current(self):
        """ Return the element at the cursor. """
        return self._data[self._cursor]

    def set_current(self, elem):
        """ Replace the element at the cursor with $elem. """
        self._data[self._cursor] = elem 

    def reduced_cursor(self):
        """ The number of queue (!) elements that with an index
        <= than the cursor."""
        ans = 0
        for i in range(self._cursor):
            if self._data[i].is_in_queue():
                ans += 1
        return ans

    def load(self, filename):
        """ Loads input file to self._data. """
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
                element = DataElement()             
                
                if not len(fields) == len(field_names):
                    raise (ValueError, "The number of supplied field_names (%d) doesn't match the number of "
                                       "fields in the file %s (%d)." % (len(field_names), filename, len(fields)))
                
                for i in range(len(fields)):
                    element.set_field(field_names[i], fields[i])   

                # for tangorin:
                # if word doesn't contain any kanji, then the expression field will be empty 
                # and you have to take the kana field instead!
                # Maybe implement that int element.set_fields_hook instead?
                if "Expression" in field_names and "Kana" in field_names:
                    logger.debug("Expression from Kana.")
                    if not element.get_expression():
                        element.set_expression(element.get_field("Kana"))

                element.set_fields_hook()
                self._data.append(element)
                logger.debug("Appended data element.")

    # ----------- Statistics --------------

    def count_data(self, boolean):
        """ Count all data entries with boolean(entry) == True """
        i = 0
        for entry in self._data:
            if boolean(entry):
                i += 1
        return i

    def len_all(self):
        """ Returns the number of all elements. """
        return self.count_data(lambda e: True)

    def len_added(self):
        """ Returns the number of all elements that
        were already added.  """
        return self.count_data(lambda e: e.is_added())

    def len_dupe(self):
        """ Returns the number of all elements that were
        classified as duplicates. """
        return self.count_data(lambda e: e.is_dupe())
        
    def len_queue(self):
        """ Returns the number of all elements that are
        currently in the queue. """
        return self.count_data(lambda e: e.is_in_queue())

    # ----------- Return subsets --------------

    def get(self, boolean):
        """ Returns list with all elements with 
        boolean(element) == True. """
        ret = []
        for entry in self._data:
            if boolean(entry):
                ret.append(entry)
        return ret


    def get_all(self):
        """ Returns list of all elements. """
        return self.get(lambda e: True)

    def get_added(self):
        """ Returns list of all elements that were 
        already added. """
        return self.get(lambda e: e.is_added())

    def get_dupe(self):
        """ Returns list of all elements that were
        classified as duplicates. """
        return self.get(lambda e: e.is_dupe())
        
    def get_queue(self):
        """ Returns list of all elements that are currently
        in the queue. """
        return self.get(lambda e: e.is_in_queue())

    # --------------- Navigate ------------------

    def go(self, func, start=None, dry=False):
        """ Updates self._cursor. 
        Starts with cursor = $start (default: func(self.cursor)
        and repeatedly call cursor = fun(cursor).
        Once the element at cursor is an element that should be in 
        the queue, we set self._cursor = cursor.
        Returns True if self._cursor was changed, False otherwise. 
        If dry == True: self._cursor remains untouched, only the
        return value is given."""
        
        if not dry:
            print("Manipulating cursor.")

        old_cursor = self._cursor
        new_cursor = self._cursor
        
        if start is None:
            # do NOT use "if not start", because start = 0 gets 
            # also evaluated as False.
            start = func(self._cursor)
        
        cursor = start
        
        while cursor in range(len(self._data)):
            if self._data[cursor].is_in_queue():
                new_cursor = cursor
                break 
            else:
                if not dry:
                    print("Skipping element %d" % cursor)
            cursor = func(cursor)
        
        if not dry:
            self._cursor = new_cursor

        if not dry:
            print("Cursor is now %d" % self._cursor)
            print("Reduced cursor is now %d" % self.reduced_cursor())

        return new_cursor == old_cursor

    def go_next(self, dry=False):
        """ Go to next queue element 
        (i.e. sets self._cursor to the index of the next queue element)
        Returns False if we are already at the last queue element.
        If dry == True: self._cursor remains untouched, only the
        return value is given. """
        return self.go(lambda x: x+1, dry=dry)

    def go_previous(self, dry=False):
        """ Go to previous queue element 
        (i.e. sets self._cursor to the index of the previous queue element)
        Returns False if we are already at the first queue element.
        If dry == True: self._cursor remains untouched, only the
        return value is given. """

        return self.go(lambda x: x-1, dry=dry)

    def go_first(self):
        """ Go to first queue element 
        (i.e. sets self._cursor to the index of the first queue element)
        Returns False if we are already at the first queue element. """
        
        return self.go(lambda x: x+1, start=0)
        
    def go_last(self):
        """ Go to last queue element 
        (i.e. sets self._cursor to the index of the last queue element)
        Returns False if we are already at the last queue element. """
        
        return self.go(lambda x: x-1, start=len(self._data)-1)

    # ------------------ Booleans --------------------

    def is_go_previous_possible(self):
        return self.go_next(dry=True)

    def is_go_next_possible(self):
        return self.go_previous(dry=True)

    def is_queue_empty(self):
        return self.len_queue() == 0

    def is_in_queue(self, exp):
        """ """
        # todo: make real thing
        if len(exp) >= 3:
            if exp in self.get_current().get_expression():
                return True
        else:
            delims = [',', ';', '・'.decode('utf-8')]
            exps = split_multiple_delims(self.get_current().get_expression(), delims)
            if exp in exps:
                return True
        return False
            

if __name__ == "__main__":
    # for testing purposes.
    import os.path
    ds = DataSet()
    filename = "tan.csv"
    if os.path.exists(filename):
        ds.load(filename)
        # set some duplicated events.
        for i_ in [1, 2, 5]:
            ds._cursor = i_
            element_ = ds.get_current()
            element_.set_dupe(True)
            ds.set_current(element_)
        ds.go_first()
    else:
        print("Test file %s not found." % filename)