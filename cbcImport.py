#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aqt.addcards import AddCards  # addCards dialog
from cbcimport.ui import CbcImportUi
from anki.hooks import addHook, runHook, wrap

myImport = CbcImportUi()

# generate new hooks
AddCards.addHistory = wrap(AddCards.addHistory, lambda *args: runHook("addHistory", *args))
AddCards.setupEditor = wrap(AddCards.setupEditor, lambda editor: runHook("setupEditor", editor))
AddCards.addCards = wrap(AddCards.addCards, lambda add_cards_obj: runHook("addCards", add_cards_obj))

# add functions to those hooks
addHook("setupEditor", myImport.on_editor_opened)
addHook("unloadProfile", myImport.save)
addHook("addCards", myImport.on_cards_added)
addHook("addHistory", myImport.on_add_history)
