#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict
from .util import split_multiple_delims


class Word(object):
    """ Contains information about one word of vocabulary.
    All data fields can be accessed by Word[field_name].
    Note however that the expression should be accessed by Word.exression! """
    # future: warning if accessed otherwise?
    # ========================= [ Basics ] =========================

    def __init__(self):
        # The fields that are to be synchronized with the anki note:
        self._fields = {}  # type: Dict[str, str]

        # cleanup: Is this nescessary?
        # Name of the expression field
        self.expression_field = "Expression"
        self.kana_field = "Kana"

        # Queue attributes
        self.is_dupe = False  # type: bool
        self.is_added = False  # type: bool
        self.is_blacklisted = False  # type: bool

        # MISC
        self.reverse_splitting = True  # type:bool

    # ========================= [ Getters, Setters & Co ] =========================

    def __getitem__(self, item):
        return self._fields[item]

    def __setitem__(self, key, value):
        self._fields[key] = value

    def __contains__(self, item):
        return item in self._fields

    def keys(self):
        return self._fields.keys()

    @property
    def expression(self):
        # we need this for importing from the Tangorin online dictionary:
        # if the expression doesn't contain any Kanji, then the Expression field might
        # be empty and only the kana field has an entry. We return that one instead.
        if not self.__contains__(self.expression_field) and self.__contains__(self.kana_field):
            self.__setitem__(self.expression_field, self.__getitem__(self.kana_field))
        return self.__getitem__(self.expression_field)

    @property
    def splitted_expression(self):
        """ Returns the expression field splitted up into different expressions/writings.
        E.g. If the expression is "そびえる・聳える", returns ["そびえる", "聳える"].
        The list should be sorted in such a way that the most frequent expression comes first."""
        # We use a getter/setter interface here, because this allows form some
        # processing.
        delims = [u",", u";", u"、", u"；", u"・"]
        splitted = split_multiple_delims(self.expression, delims=delims)
        if self.reverse_splitting:
            return reversed(splitted)
        else:
            return splitted

    # ========================= [ Other magic methods] =========================

    def __str__(self):
        return "<{} object for Expression {}>".format(self.expression)

    def __repr__(self):
        return self.__str__()
