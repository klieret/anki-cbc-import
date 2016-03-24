#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aqt.addcards import AddCards  # addCards dialog
from cbcimport.ui import CbcImportUi
from anki.hooks import addHook, runHook, wrap

myImport = CbcImportUi()

# generate new hooks
AddCards.addHistory = wrap(AddCards.addHistory, lambda *args: runHook("addHistory", *args))
AddCards.setupEditor = wrap(AddCards.setupEditor, lambda add_cards_obj: runHook("addEditorSetup", add_cards_obj))
AddCards.addCards = wrap(AddCards.addCards, lambda add_cards_obj: runHook("tooltip", add_cards_obj))

# add functions to those hooks
addHook("addEditorSetup", myImport.setup_my_menu)
addHook("unloadProfile", myImport.save)
addHook("tooltip", myImport.added_tooltip)
addHook("addHistory", myImport.card_added)
