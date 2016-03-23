#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict


class Word(object):
    """ Contains information about one word of vocabulary. """
    def __init__(self):
        # The fields that are to be synchronized with
        # the anki note.
        # Should be of type
        # {"fieldname":"value", ...}
        self._fields = {}  # type: Dict[str, str]
        self.is_dupe = False  # type: bool
        self.is_added = False  # type: bool
        self.is_blacklisted = False  # type: bool

    # =============== [Getters & Setters] ===============

    def __getitem__(self, item):
        return self._fields[item]

    def __setitem__(self, key, value):
        self._fields[key] = value

    @property
    def expression(self):
        """ Returns the expression (word of vocabulary). """
        # We use a getter/setter interface here, because this allows form some
        # processing.
        return self.__getitem__("Expression").split(u"・")[-1]

    @expression.setter
    def expression(self, value):
        self.__setitem__("Expression", value)
