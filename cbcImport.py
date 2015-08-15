#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" cbcImport -- and interface to add notes to Anki on a 
case by case basis. """

from aqt import mw # main window
from aqt.editor import Editor
from aqt.addcards import AddCards # addCards dialog
from aqt.utils import shortcut, tooltip, getSaveFile
from aqt.qt import *

from anki.hooks import addHook, runHook, wrap

from ignore_dupes import expressionDupe

import csv
import os.path
import glob
import copy
import os

from data_classes import *
from util import *

import logging
logger = logging.getLogger("cbcImport:main")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("log.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

# todo: duplicates!

# TODO: FIELDS MORE CLEAR (MULTIPLE USED EXPRESSION ETC.)
# TODO: Laden von Dateinamen an Bauen von Menu koppeln, nicht einfach an Init (da nur bei Start von Anki ausgeführt...) 
# TODO: keine Checks etc., wenn noch nicht mal mehr Datei geladen.
# TODO: Button zum entladen von Datein
# Problem: Curser bleibt stehen, wenn jetzt QUEUE verkürzt wird
# evtl. curser out of range?

# 1. RESTART ANKI AFTER EACH EDIT (ELSE IT WON'T TAKE EFFECT)
# 2. NOTE THAT IDENTATION MATTERS IN PYTHON. 
# 3. DON'T USE SPACES TO INDENT IN THIS FILE.



class cbcImport():
    def __init__(self):
        """ init and basic configuration """
        # ----------- BEGIN CONFIG -----------   
        # file to import (change the "..." part)
        #self.importFile=os.path.expanduser("~/Desktop/tangorin_38567.csv")
        #self.importFile=os.path.expanduser('~/Desktop/rest.csv')
        self.defaultDir = os.path.expanduser("~/Desktop/")
        try:
            # last file of all files that are on Desktop and have extension .csv
            self.importFile = glob.glob(os.path.expanduser("~/Desktop/*.csv"))[-1] 
        except:
            self.importFile = None
        # delimiter of the input file (character that separates
        # different rows). E.g. '\t' for Tabulator, ';' for ; etc. 
        self.delim = '\t'
        
        # character encoding to be used for input and output
        self.encoding = 'utf-8'
        if self.importFile:
            importFileName, importFileExt = os.path.splitext(self.importFile)
        else:
            importFileName = None
            importFileExt = None
        # files where the subset of added/remaining Cards will be Saved
        # (by default: self.importFile - file ending + "added"/"rest" + extension)
        # Note that the file contents will be overwritten!
        # If self.addedFile=None or False or "" is specified
        # no output will be created for addedFile (restFile analogous)
        self.addedFile = None
        self.restFile = os.path.expanduser('~/Desktop/rest.csv')
        #self.addedFile=os.path.expanduser('~/Desktop/added.csv')
        #self.restFile=os.path.expanduser('~/Desktop/rest.csv')
        #self.addedFile=importFileName+"_added"+importFileExt
        #self.restFile=importFileName+"_rest"+importFileExt
        
        self.careForDupes = True # Should dupes be treated differently?
        self.createEmptyFiles = False # Should export files created even if data empty?
        self.defaultEditor = "leafpad "   # Command to run default editor 
                                        # (include space or switch)
        
        # ----------- END CONFIG -----------
        
        self.data =  DataSet()
        
        self.e = None     # instance of the Editor window
        self.mw = None    # instance of main window
        
        # was last Card added to self.added?
        self.lastAdded = None
        
        self.buttons = {}

    def wrap(self, note, current):
        """ Updates note $note with data from $current. """
        
        # ----------- BEGIN CONFIG -----------
        self.delim = unicode('・', self.encoding)
        
        # TODO splitting as separate method
        def enum(string):
            split = string.split('/')
            out = ""
            n = len(split)
            if n == 1:
                return string
            else:
                for i in range(n):
                    out += str(i+1)+". "+split[i]+'<br>'
            return out.strip()
        
        note['Expression'] = current.get_expression()
        note['Meaning'] = enum(current.get_field('Meaning'))
        # ----------- END CONFIG -----------
        
        return note

    def insert(self):
        """ Inserts an entry from self.queue
        into the Anki Dialog """

        if self.data.is_queue_empty():
            tooltip(_("Queue is empty!"),period=1000)
            return
        elif self.data.is_go_next_possible():
            tooltip(_("Was last entry!"),period=1000)
        
        self.clean()    # remove All field entries
        
        current = self.data.get_current() #source
        note = copy.copy(self.e.note)         #target
        
        self.e.setNote(self.wrap(note, current))
        
        self.runHooks()
        self.updateStatus()
    
    def clean(self):
        """ Resets all fields. """
        for field in mw.col.models.fieldNames(self.e.note.model()):
            self.e.note[field] = ''
        self.e.note.flush()

    # Loading/Saving file
    # ------------------------

    def newInputFile(self):
        filters = "csv Files (*.csv);;All Files (*)"
        import_file = QFileDialog.getSaveFileName(None, "Pick a file to import.", 
            self.defaultDir, filters, options=QFileDialog.DontConfirmOverwrite)
        if import_file:
            self.importFile = import_file
        self.updateStatus()
    
    def load(self):
        """ Loads input file to self.data. """
        self.data = DataSet()

        if not self.importFile:
            tooltip(_("No import file specified"),period=1500)
        try:
            logger.debug("Loading. ")
            self.data.load(self.importFile)
        except ZeroDevisionError:
            logger.debug("Loading exception!")
            tooltip(_("Could not open input file %s" % self.importFile),period=1500)

        self.update_duplicates()
        # status
        self.updateStatus()
        tooltip(_("All: %d (Dupe: %d)" % (self.data.len_all(), self.data.len_dupe())), period=1500)
    
    def update_duplicates(self):
        """ If self.careForDupes==True: updates the duplicate status of all
        entries in the data. Else: does nothing. 
        Return value (bool): Was something changed?"""
        
        if not self.careForDupes:
            return False
        
        changes = False
        
        for i in range(len(self.data._data)):
            entry = self.data._data[i]
            delims = [',', ';', '・'.decode('utf-8')]
            exps = split_multiple_delims(entry.get_expression(), delims)
            # if any of the partial expressions is a duplicate
            # we mark the whole db entry as a duplicate!
            for exp in exps:
                if expressionDupe(self.mw.col, exp):
                    if not entry.is_dupe():
                        changes = True
                    entry.dupe = True
                    # write back!
                    self.data._data[i] = entry
                    print("Marked Entry %s as duplicate." % entry.get_expression())
                    break
        return changes


    def save(self):
        """ Saves self.added and self.rest to the resp. files """
        pass

        # todo

        # if self.addedFile and (self.createEmptyFiles or len(self.added)>0):
        #     try:
        #         with open(self.addedFile,'wb') as csvfile:
        #             writer=csv.writer(csvfile, delimiter=self.delim)
        #             for row in self.added:
        #                 row=[c.encode(self.encoding) for c in row]
        #                 writer.writerow(row)
        #     except:
        #         tooltip(_("Could not open output file %s" % self.addedFile),period=1500)
                
        # if self.restFile and (self.createEmptyFiles or len(self.rest)>0):
        #     try:
        #         with open(self.restFile,'wb') as csvfile:
        #             writer=csv.writer(csvfile, delimiter=self.delim)
        #             for row in self.rest:
        #                 row=[c.encode(self.encoding) for c in row]
        #                 writer.writerow(row)
        #     except:
        #         tooltip(_("Could not open output file %s" % self.restFile),period=1500)

    def saveButtonPushed(self):
        """ What happens if save button is pushed:
        Show tooltip and save."""
        self.save()
        # # tooltip
        # text=""
        # if self.addedFile: 
        #     text+="Saved added "
        # if self.restFile:
        #     text+="Saved rest"
        # if text=="":
        #     text+="NO FILE TO SAVE"
        # tooltip(_(text), period=1500)

    def show(self):
        """ Opens input file in an external editor. """
        if self.importFile:
            os.system("%s %s &" % (self.defaultEditor, self.importFile))
        else:
            tooltip(_("No input File!"), period=1500)
    
    # Controlling self.Idx
    # -----------------------------
    
    def last(self):
        """ Inserts last entry. """
        self.data.go_last()
        self.insert()
    
    def next(self):
        """ Inserts next entry. """
        self.data.go_next()
        self.insert()
    
    def previous(self):
        """ Inserts previous entry. """
        self.data.go_previous()
        self.insert()
    
    def first(self):
        """ Inserts first entry. """
        self.data.go_first()
        self.insert()
    
    def reverse(self):
        """ Reverses the ordering of the queue. """
        if self.data.is_queue_empty():
            tooltip(_("Queue is empty!"),period=1000)
            return  
        self.data.reverse()
        self.updateStatus()
        
    # Running Hooks and similar
    # -------------------------------------
    
    def runHooks(self):
        """ Runs the hook 'editFocusLost'. 
        Expl.: A lot of other plugins (e.g. furigana completion etc.) activate as 
        soon as 'editFocusLost' is called (normally triggered after manually 
        editing a field). Calling it directly saves us the trouble of clicking
        into the 'Expression' field and outside again to trigger this. """
        changedFields = ['Expression','Meaning']
        for field in changedFields:
            fieldIdx = mw.col.models.fieldNames(self.e.note.model()).index(field)
            runHook('editFocusLost',False,self.e.note,fieldIdx)
        self.e.loadNote()
    
    def cardAdded(self, obj, note):
        """ This function gets called once a card is added and
        is needed to update self.added (list of added cards) """
        self.lastAdded = False
        # save user input
        # this seems to be neccessary
        note.flush()
        if self.data.is_go_next_possible():
            # current queue Element Expression
            current = self.data.get_current()
            exp = note['Expression']
            # we have to check if the we really are adding an element
            # of the queue. Problem is that we want to allow some tolerance
            
            if self.data.is_in_queue(exp):
                self.lastAdded = True
                current.is_added = True
                self.data.set_current(current)

        self.updateStatus()
        
    def myTooltip(self,*args):
        """ Has to be called separately to overwrite native
        'Added' tooltip. """
        if self.lastAdded:
            tooltip(_("Added to added"), period=1000)
        else:
            tooltip(_("NOT ADDED TO ADDED!"), period=1000)

    # Setup Menu
    # ----------------------------------------

    def setupMyMenu(self, AddCardsObj):
        """ Creates the line of buttons etc. to control this addon. """
        self.e = AddCardsObj.editor
        self.mw = AddCardsObj.mw
        # adapted from from /usr/share/anki/aqt/editor.py Lines 350
        self.newIconsBox = QHBoxLayout()
        if not isMac:
            self.newIconsBox.setMargin(6)
            self.newIconsBox.setSpacing(0)
        else:
            self.newIconsBox.setMargin(0)
            self.newIconsBox.setSpacing(14)
        self.e.outerLayout.addLayout(self.newIconsBox)
        # Buttons
        # Buttons starting with cbcQ_ are only active if queue is non empty
        self.addMyButton("cbc_NewInputFile", self.newInputFile, text="Choose File", tip="Choose new input file.", size="30x120", )
        self.addMyButton("cbc_Load", self.load, text="Load", tip="Load file", size="30x60", )
        self.addMyButton("cbc_Show", self.show, text="Show", tip="Show file", size="30x60", )
        self.addMyButton("cbcQ_Reverse", self.reverse, text="Reverse", tip="Reverse Order", size="30x60", )
        self.addMyButton("cbc_Save", self.saveButtonPushed, text="Save", tip="Saves all added resp. all remaining notes to two files.", size="30x60", )
        self.addMyButton("cbcQ_First", self.first, text="<<", tip="Fill in first entry", size="30x50",)
        self.addMyButton("cbcQ_Previous", self.previous, text="<", tip="Fill in previous entry", size="30x50" , )
        self.addMyButton("cbcQ_Fill", self.insert, text="X", tip="Fill in form (Ctrl+F)", size="30x50",  key="Ctrl+F")
        self.addMyButton("cbcQ_Next", self.next, text=">", tip="Fill in next entry (Ctrl+G)", size="30x50", key="Ctrl+G")
        self.addMyButton("cbcQ_Last", self.last, text=">>", tip="Fill in last entry", size="30x50" , )
        # self.updateButtonStates() # maybe tooltips are better...
        # Status Field
        self.statusIconsBox = QHBoxLayout()
        if not isMac:
            self.statusIconsBox.setMargin(6)
            self.statusIconsBox.setSpacing(0)
        else:
            self.statusIconsBox.setMargin(0)
            self.statusIconsBox.setSpacing(14)
        self.e.outerLayout.addLayout(self.statusIconsBox)
        self.status=QLabel()
        self.updateStatus()
        self.statusIconsBox.addWidget(self.status)
    
    def addMyButton(self, name, func, key=None, tip=None, size=True, text="", check=False):
        """ Shortcut to add a new button. """       
        # adapted from from /usr/share/anki/aqt/editor.py Lines 308..
        b = QPushButton(text)
        # For some reason, if you don't deactivate manually the following
        # two options, the first button will start to behave like the Add-Button.
        b.setAutoDefault(False)
        b.setDefault(False)
        if check:
            b.connect(b, SIGNAL("clicked(bool)"), func)
        else:
            b.connect(b, SIGNAL("clicked()"), func)
        if size:
            if size.split('x')[0]:
                b.setFixedHeight(int(size.split('x')[0]))
            b.setFixedWidth(int(size.split('x')[1]))
        if not text:
            b.setIcon(QIcon(":/icons/%s.png" % name))
        if key:
            b.setShortcut(QKeySequence(key))
        if tip:
            b.setToolTip(shortcut(tip))
        if check:
            b.setCheckable(True)
        self.newIconsBox.addWidget(b)
        self.buttons[name] = b
        return b
    
    def updateButtonStates(self):
        for buttonName in self.buttons:
            if buttonName.startswith('cbcQ_'):
                self.buttons[buttonName].setEnabled(not self.is_queue_empty())

    def updateStatus(self):
        """ Updates button texts e.g. to display 
        number of remaining entries etc. """
        
        def short(string):
            if not string:
                return "None"
            mlen = 10
            if len(string)<=mlen:
                return string
            return "..."+string[-mlen:]
        
        text = '<b>In:</b> "%s" ' % short(self.importFile)
        text += '<b>OutA:</b> "%s" ' % short(self.addedFile)
        text += '<b>OutR:</b> "%s" | ' % short(self.restFile)
        text += "<b>Idx:</b> %d/%d <b>Add:</b> %d <b>Dup:</b> %d | " % (self.data.reduced_cursor(),self.data.len_queue(),self.data.len_added(),self.data.len_dupe())
        text += "<b>LA:</b> %s" % format_bool_html(self.lastAdded) 
        self.status.setText(text)   




myImport = cbcImport()

# generate new hooks
AddCards.addHistory = wrap(AddCards.addHistory, lambda *args: runHook("addHistory", *args))
AddCards.setupEditor = wrap(AddCards.setupEditor, lambda AddCardsObj: runHook("addEditorSetup", AddCardsObj))
AddCards.addCards = wrap(AddCards.addCards, lambda AddCardsObj: runHook("tooltip", AddCardsObj))

# add functions to those hooks
addHook("addEditorSetup", myImport.setupMyMenu)
addHook("unloadProfile", myImport.save)
addHook("tooltip", myImport.myTooltip)
addHook("addHistory", myImport.cardAdded)