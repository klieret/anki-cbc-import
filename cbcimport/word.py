#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict
from .util import split_multiple_delims
from .log import logger

try:
    from ignore_dupes.ignore_dupes import expression_dupe
except ImportError:
    logger.warning("Couldn't import the ignore_dupes function. Will replace it with a dummy function.")

    # noinspection PyUnusedLocal
    def expression_dupe(*args, **kwargs):
        return False


class Word(object):
    """ Contains information about one word of vocabulary.
    All data fields can be accessed by Word[field_name].
    Only note that we rigged it so that Word[Word.expression_field] returns
    Word[Word.kana_field] if the Kana field is set but the Expression field is not.
    The real Expression field can still be accessed as Word._fields[Word.expression_field].
    As basic fields such as expression, kana, meaning should be accessible without having to
    use Word[Word.expression_field] etc, they are also defined as properties and will return
    empty strings if the field is not set yet."""
    # Note: We use a lot of property decorators in this class, beccause it makes it easier to
    #       switch between internal variables and funtions.
    # ========================= [ Basics ] =========================

    def __init__(self):
        # The fields that are to be synchronized with the anki note:
        self._fields = {}  # type: Dict[str, str]

        # Name of the expression field
        # todo: should be loaded from config file
        self.expression_field = "Expression"
        self.meaning_field = "Meaning"
        self.kana_field = "Kana"

        # Queue attributes
        self.is_dupe = False  # type: bool
        self.is_added = False  # type: bool
        self.is_blacklisted = False  # type: bool

        # MISC
        self.reverse_splitting = True  # type:bool

    # ========================= [ Getters, Setters & Co ] =========================

    def __getitem__(self, item):
        if item == self.expression_field:
            if not self.__contains__(self.expression_field) and self.__contains__(self.kana_field):
                return self.__getitem__(self.kana_field)
        return self._fields[item]

    def __setitem__(self, key, value):
        self._fields[key] = value

    def __contains__(self, item):
        return item in self._fields

    def keys(self):
        return self._fields.keys()

    def check_duplicate(self):
        logger.debug(u"Checking for duplicate: {}".format(unicode(self.expression)))
        self.is_dupe = expression_dupe(self.expression)

    @property
    def expression(self):
        try:
            return self.__getitem__(self.expression_field)
        except KeyError:
            return ""

    @property
    def meaning(self):
        try:
            return self.__getitem__(self.meaning_field)
        except KeyError:
            return ""

    @property
    def kana(self):
        try:
            self.__getitem__(self.kana_field)
        except KeyError:
            return ""

    @property
    def splitted_expression(self):
        """ Returns the expression field splitted up into different expressions/writings.
        E.g. If the expression is "そびえる・聳える", returns ["そびえる", "聳える"].
        The list should be sorted in such a way that the most frequent expression comes first."""
        # We use a getter/setter interface here, because this allows form some
        # processing.
        delims = [u",", u";", u"、", u"；", u"・"]
        splitted = split_multiple_delims(unicode(self.expression), delims=delims)
        if self.reverse_splitting:
            splitted.reverse()
        print(splitted)
        return splitted

    @property
    def splitted_meaning(self):
        """ If there are several meanings, a list of all of those meanings is returned. """
        delims = [u"/"]  # this is specific for the platform your importing from. Here it's tangorin.
        return split_multiple_delims(self.meaning, delims=delims)

    @property
    def formatted_meaning(self):
        """ Formats the meaning field. In particular, if there are several meanings, they
        are enumerated.
        """
        split = self.splitted_meaning
        if len(split) == 1:
            return split[0]
        lines = []
        for item_no, item in enumerate(split):
            lines.append("{}. {}".format(item_no + 1,  item.strip()))
        return '<br>'.join(lines)

    # ========================= [ Other magic methods] =========================

    def __str__(self):
        return u"<{} object for Expression {}>".format(self.__class__.__name__, self.expression)

    def __repr__(self):
        return self.__str__()
