#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aqt import mw # main window
from aqt.editor import Editor
from aqt.addcards import AddCards # addCards dialog
from aqt.utils import shortcut
from aqt.qt import *

from anki.hooks import addHook, runHook, wrap

import csv
import os.path


class cbcImport():
	def __init__(self):
		""" init and basic configuration """
		# ----------- CONFIG -----------
		
		# file to import (change the "..." part)
		self.importFile=os.path.expanduser("~/Desktop/tangorin_38567.csv")
		# delimiter of the input file (character that separates
		# different rows). E.g. '\t' for Tabulator, ';' for ; etc. 
		self.delim='\t'
		
		# character encoding to be used for input and output
		self.encoding='utf-8'
		
		importFileName,importFileExt=os.path.splitext(self.importFile)
		# files where the subset of added/remaining Cards will be Saved
		# (by default: self.importFile - file ending + "added"/"rest" + extension)
		# Note that the file contents will be overwritten!
		# If self.addedFile=None or False or "" is specified
		# no output will be created for addedFile (restFile analogous)
		self.addedFile=importFileName+"_added"+importFileExt
		self.restFile=importFileName+"_rest"+importFileExt
		
		# ----------- END CONFIG -----------
		
		# data from import File will be saved in self.data:
		self.data=[] # format: [[field1,field2,...]]
		# subsets of self.data to save all added cards resp.
		# all remaining cards.
		self.added=[]
		self.rest=[]
		# how many of the vocabulary have we already added:
		self.currentIdx=0
		# saves the instance of the Editor window
		self.e=None
		self._buttons={}

	def insert(self):
		""" Inserts an entry from self.data
		into the Anki Dialog """
		self.clean()
		if not self.currentIdx < len(self.data):
			# should only happen if data could not
			# be imported.
			return
		current=self.data[self.currentIdx]
		note=self.e.note
		# ----------- CONFIG -----------
		delim=unicode('・',self.encoding)
		note['Expression']=current[0].split(delim)[-1]
		note['Meaning']=current[2]
		# ----------- END CONFIG -----------
		self.e.note=note
		self.e.note.flush()
		self.e.loadNote()
		self.runHooks()
		self.updateStatus()

	def load(self):
		""" Loads input file to self.data. """
		print("LLLoad")
		self.data=[]
		with open(self.importFile,'r') as csvfile:
			reader=csv.reader(csvfile, delimiter=self.delim)
			for row in reader:
				self.data.append([c.decode(self.encoding) for c in row])
		self.updateStatus()
	
	# Saving....
	def updateRest(self):
		""" Builds self.rest from self.data and self.added """
		for i in range(len(self.data)):
			if not self.data[i] in self.added:
				self.rest.append(self.data[i])
	def save(self):
		""" Saves self.added and self.rest to the resp. files """
		if self.addedFile:
			with open(self.addedFile,'wb') as csvfile:
				writer=csv.writer(csvfile, delimiter=self.delim)
				for row in self.added:
					row=[c.encode(self.encoding) for c in row]
					writer.writerow(row)
		if self.restFile:
			self.updateRest()
			with open(self.restFile,'wb') as csvfile:
				writer=csv.writer(csvfile, delimiter=self.delim)
				for row in self.rest:
					row=[c.encode(self.encoding) for c in row]
					writer.writerow(row)
	
	def clean(self):
		""" Resets all fields. """
		for field in mw.col.models.fieldNames(self.e.note.model()):
			self.e.note[field]=''
		self.e.note.flush()
	
	# Controlling self.Idx: .......
	def last(self):
		""" Inserts last entry. """
		self.currentIdx=len(self.data)-1
		self.insert()
	def next(self):
		""" Inserts next entry. """
		if self.currentIdx<len(self.data)-1:
			self.currentIdx+=1
		self.insert()
	def previous(self):
		""" Inserts previous entry. """
		if self.currentIdx>=1:
			self.currentIdx-=1
		self.insert()
	def first(self):
		""" Inserts first entry. """
		self.currentIdx=0
		self.insert()
	def reverse(self):
		""" Reverses the ordering. """
		self.data.reverse()
		self.currentIdx=len(self.data)-1-self.currentIdx
		self.updateStatus()
		

	
	def runHooks(self):
		""" Runs the hook 'editFocusLost'. 
		Expl.: A lot of other plugins (e.g. furigana completion etc.) activate as 
		soon as 'editFocusLost' is called (normally triggered after manually 
		editing a field). Calling it directly saves us the trouble of clicking
		into the 'Expression' field and outside again to trigger this. """
		changedFields=['Expression','Meaning']
		for field in changedFields:
			fieldIdx=mw.col.models.fieldNames(self.e.note.model()).index('Expression')
			runHook('editFocusLost',False,self.e.note,fieldIdx)
		self.e.loadNote()
	
	def cardAdded(self, obj, note):
		""" This function gets called, once a card is added and
		is needed to update self.added (list of added cards) """
		current=self.data[self.currentIdx]
		if note['Expression'] in current[0]:
			self.added.append(current)
		self.updateStatus()
	
#	def wrapper(self,AddCardsObj):
#		self.setupMyButtons(AddCardsObj.editor)
		
	def fix(self,AddCardsObj):	
		AddCardsObj.addButton.setShortcut(QKeySequence("Ctrl+Return"))
	
	def setupMyButtons(self,AddCardsObj):
		self.e=AddCardsObj.editor
		# adapted from from /usr/share/anki/aqt/editor.py Lines 350
		self.newIconsBox=QHBoxLayout()
		if not isMac:
			self.newIconsBox.setMargin(6)
			self.newIconsBox.setSpacing(0)
		else:
			self.newIconsBox.setMargin(0)
			self.newIconsBox.setSpacing(14)
		self.e.outerLayout.addLayout(self.newIconsBox)
		# Buttons
		self.addMyButton("cbcLoad", self.load, text="Load", tip="Load file", size="30x60", )
		self.addMyButton("cbcReverse", self.reverse, text="Reverse", tip="Reverse Order", size="30x60", )
		self.addMyButton("cbcFirst", self.first, text="<<", tip="Fill in first entry", size="30x50",)
		self.addMyButton("cbcPrevious", self.previous, text="<", tip="Fill in previous entry (Ctrl+H)", size="30x50" , key="Ctrl+H")
		self.addMyButton("cbcFill", self.insert, text="X", tip="Fill in form (Ctrl+F)", size="30x50",  key="Ctrl+F")
		self.addMyButton("cbcNext", self.next, text=">", tip="Fill in next entry (Ctrl+G)", size="30x50", key="Ctrl+G")
		self.addMyButton("cbcLast", self.last, text=">>", tip="Fill in last entry", size="30x50" , )
		# Status Field
		self.status=QLabel()
		self.updateStatus()
		self.newIconsBox.addWidget(self.status)
	
	def addMyButton(self, name, func, key=None, tip=None, size=True, text="", check=False):
		# adapted from from /usr/share/anki/aqt/editor.py Lines 308..
		b = QPushButton(text)
		# For some reason, if you don't deactivate those
		# two, the first button will start to behave like the Add-Button.
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
		self._buttons[name] = b
		return b
	
	def updateStatus(self):
		""" Updates button texts e.g. to display 
		number of remaining entries etc. """
		numbers=[self.currentIdx+1,len(self.data),len(self.added),len(self.data)-len(self.added)]
		#form=["{:3}".format(n) for n in numbers]
		self.status.setText(" Idx: %s/%s Add: %s Rem: %s" % tuple(numbers))	

def addNoteHook(*args):
	runHook("cardAdded",*args)


myImport=cbcImport()
AddCards.addHistory=wrap(AddCards.addHistory,lambda *args: runHook("addHistory",*args))
AddCards.setupEditor=wrap(AddCards.setupEditor,lambda AddCardsObj: runHook("addEditorSetup",AddCardsObj))
#AddCards.setupButtons=wrap(AddCards.setupButtons,myImport.fix)

#addHook("addHistory",myImport.cardAdded)
addHook("addEditorSetup",myImport.setupMyButtons)
addHook("unloadProfile",myImport.save)
