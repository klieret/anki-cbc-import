#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aqt import mw # main window
from aqt.editor import Editor
from aqt.addcards import AddCards # addCards dialog
from aqt.utils import shortcut, tooltip, getSaveFile
from aqt.qt import *

from anki.hooks import addHook, runHook, wrap

import csv
import os.path
import glob
import copy


# TODO: FIELDS MORE CLEAR (MULTIPLE USED EXPRESSION ETC.)

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
		self.importFile=glob.glob(os.path.expanduser("~/Desktop/*.csv"))[-1] # last file of all files that are on Desktop and have extension .csv
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
		self.addedFile=None
		self.restFile=os.path.expanduser('~/Desktop/rest.csv')
		#self.addedFile=os.path.expanduser('~/Desktop/added.csv')
		#self.restFile=os.path.expanduser('~/Desktop/rest.csv')
		#self.addedFile=importFileName+"_added"+importFileExt
		#self.restFile=importFileName+"_rest"+importFileExt
		
		self.careForDupes=True # Should dupes be treated differently?
		
		# ----------- END CONFIG -----------
		
		# data from import File will be saved in self.data
		# format: [[field1,field2,...],[field1,field2,...]]
		self.data=[] 
		# subsets of self.data 
		self.added=[] 	# added cards
		self.rest=[] 	# remaining cards
		self.dupe=[] 	# duplicates with anki Cards
		self.queue=[] 	# currentQueue
		
		self.currentIdx=0 	# cursor in self.queue
		
		self.e=None		# instance of the Editor window
		self.mw=None	# instance of main window
		
		# was last Card added to self.added?
		self.lastAdded=None
		
		self.buttons={}

	def wrap(self, note, current):
		""" Updates note $note with data from $current. """
		
		# ----------- BEGIN CONFIG -----------
		delim=unicode('・',self.encoding)
		def enum(string):
			split=string.split('/')
			out=""
			n=len(split)
			if n==1:
				return string
			else:
				for i in range(n):
					out+=str(i+1)+". "+split[i]+'<br>'
			return out.strip()
		
		note['Expression']=current[0].split(delim)[-1]
		note['Meaning']=enum(current[2])
		# ----------- END CONFIG -----------
		
		return note

	def insert(self):
		""" Inserts an entry from self.queue
		into the Anki Dialog """
		if not self.currentIdx < len(self.queue):
			# empty queue
			tooltip(_("Queue is empty!"),period=1000)
			return
		
		self.clean()	# remove All field entries
		
		current=self.queue[self.currentIdx]	#source
		note=copy.copy(self.e.note) 		#target
		
		self.e.setNote(self.wrap(note,current))
		
		self.runHooks()
		self.updateStatus()
	
	def clean(self):
		""" Resets all fields. """
		for field in mw.col.models.fieldNames(self.e.note.model()):
			self.e.note[field]=''
		self.e.note.flush()

	# Loading/Saving file
	# ------------------------

	def newInputFile(self):
		importFile=QFileDialog.getSaveFileName(options=QFileDialog.DontConfirmOverwrite)
		if importFile:
			self.importFile=importFile
		self.updateStatus()
	
	def load(self):
		""" Loads input file to self.data. """
		# initialize self.data
		self.data=[]
		with open(self.importFile,'r') as csvfile:
			reader=csv.reader(csvfile, delimiter=self.delim)
			for row in reader:
				self.data.append([c.decode(self.encoding) for c in row])
		# initialize subsets
		self.fullUpdateDupes()
		self.fullUpdateRest()
		self.queue=self.rest
		# status
		self.updateStatus()
		tooltip(_("All: %d (Dupe: %d)" % (len(self.data),len(self.dupe))), period=1500)
	def fullUpdateDupes(self):
		""" If self.careForDupes==True: Finds all duplicates from self.data and
		writes them to self.dupe. Else: do nothing. """
		if not self.careForDupes:
			return
		from ignore_dupes import expressionDupe
		for item in self.data:
			delim=unicode('・',self.encoding)
			exp=item[0].split(delim)[-1]
			print("Checking %s" % exp)
			if expressionDupe(self.mw.col,exp):
				self.dupe.append(item)
	def fullUpdateRest(self):
		""" Generates self.rest from self.data by substract self.dupe and self.added. """
		self.rest=[]
		for item in self.data:
			if not item in self.dupe and not item in self.added:
				self.rest.append(item)

	def save(self):
		""" Saves self.added and self.rest to the resp. files """
		if self.addedFile:
			with open(self.addedFile,'wb') as csvfile:
				writer=csv.writer(csvfile, delimiter=self.delim)
				for row in self.added:
					row=[c.encode(self.encoding) for c in row]
					writer.writerow(row)
		if self.restFile:
			with open(self.restFile,'wb') as csvfile:
				writer=csv.writer(csvfile, delimiter=self.delim)
				for row in self.rest:
					row=[c.encode(self.encoding) for c in row]
					writer.writerow(row)

	def saveButtonPushed(self):
		""" What happens if save button is pushed:
		Show tooltip and save."""
		save()
		# tooltip
		text=""
		if self.addedFile: 
			text+="Saved added "
		if self.restFile:
			text+="Saved rest"
		if text=="":
			text+="NO FILE TO SAVE"
		tooltip(_(text), period=1500)
	
	
	# Controlling self.Idx
	# -----------------------------
	def last(self):
		""" Inserts last entry. """
		if self.currentIdx<len(self.queue)-1:
			self.currentIdx+=1
		else:
			tooltip(_("Already last card"), period=500)
		self.currentIdx=len(self.queue)-1
		self.insert()
	def next(self):
		""" Inserts next entry. """
		if self.currentIdx<len(self.queue)-1:
			self.currentIdx+=1
		else:
			tooltip(_("Already last card"), period=500)
		self.insert()
	def previous(self):
		""" Inserts previous entry. """
		if self.currentIdx>=1:
			self.currentIdx-=1
		else:
			tooltip(_("Already first card"), period=500)
		self.insert()
	def first(self):
		""" Inserts first entry. """
		self.currentIdx=0
		self.insert()
	def reverse(self):
		""" Reverses the ordering of the queue. """
		if len(self.queue)==0:
			tooltip(_("Queue is empty!"),period=1000)
			return
		self.data.reverse()
		self.added.reverse()
		self.dupe.reverse()
		self.queue.reverse()
		self.currentIdx=len(self.queue)-1-self.currentIdx
		self.updateStatus()
		
	# Running Hooks and similar
	# -------------------------------------
	
	def runHooks(self):
		""" Runs the hook 'editFocusLost'. 
		Expl.: A lot of other plugins (e.g. furigana completion etc.) activate as 
		soon as 'editFocusLost' is called (normally triggered after manually 
		editing a field). Calling it directly saves us the trouble of clicking
		into the 'Expression' field and outside again to trigger this. """
		changedFields=['Expression','Meaning']
		for field in changedFields:
			fieldIdx=mw.col.models.fieldNames(self.e.note.model()).index(field)
			runHook('editFocusLost',False,self.e.note,fieldIdx)
		self.e.loadNote()
	
	def cardAdded(self, obj, note):
		""" This function gets called, once a card is added and
		is needed to update self.added (list of added cards) """
		if len(self.data)==0:
			return
		current=self.queue[self.currentIdx]
		if note['Expression'] in current[0]:
			self.lastAdded=True
			self.added.append(current)
			self.rest.remove(current)
		else:
			self.lastAdded=False
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

	def setupMyMenu(self,AddCardsObj):
		""" Creates the line of buttons etc. to control this addon. """
		self.e=AddCardsObj.editor
		self.mw=AddCardsObj.mw
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
		# Buttons starting with cbcQ_ are only active if queue is non empty
		self.addMyButton("cbc_NewInputFile", self.newInputFile, text="Choose File", tip="Choose new input file.", size="30x120", )
		self.addMyButton("cbc_Load", self.load, text="Load", tip="Load file", size="30x60", )
		self.addMyButton("cbcQ_Reverse", self.reverse, text="Reverse", tip="Reverse Order", size="30x60", )
		self.addMyButton("cbcS_ave", self.saveButtonPushed, text="Save", tip="Saves all added resp. all remaining notes to two files.", size="30x60", )
		self.addMyButton("cbcQ_First", self.first, text="<<", tip="Fill in first entry", size="30x50",)
		self.addMyButton("cbcQ_Previous", self.previous, text="<", tip="Fill in previous entry", size="30x50" , )
		self.addMyButton("cbcQ_Fill", self.insert, text="X", tip="Fill in form (Ctrl+F)", size="30x50",  key="Ctrl+F")
		self.addMyButton("cbcQ_Next", self.next, text=">", tip="Fill in next entry (Ctrl+G)", size="30x50", key="Ctrl+G")
		self.addMyButton("cbcQ_Last", self.last, text=">>", tip="Fill in last entry", size="30x50" , )
		# self.updateButtonStates() # maybe tooltips are better...
		# Status Field
		self.statusIconsBox=QHBoxLayout()
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
				self.buttons[buttonName].setEnabled(len(self.queue)>0)

	def updateStatus(self):
		""" Updates button texts e.g. to display 
		number of remaining entries etc. """
		def short(string):
			if not string:
				return "None"
			mlen=10
			if len(string)<=mlen:
				return string
			return "..."+string[-mlen:]
		text='<b>In:</b> "%s" ' % short(self.importFile)
		text+='<b>OutA:</b> "%s" ' % short(self.addedFile)
		text+='<b>OutR:</b> "%s" | ' % short(self.restFile)
		text+="<b>Idx:</b> %d/%d <b>Add:</b> %d <b>Dup:</b> %d | " % (self.currentIdx+1,len(self.queue),len(self.added),len(self.dupe))
		text+="<b>LA:</b> %s" % str(self.lastAdded)
		self.status.setText(text)	


myImport=cbcImport()

# generate new hooks
AddCards.addHistory=wrap(AddCards.addHistory,lambda *args: runHook("addHistory",*args))
AddCards.setupEditor=wrap(AddCards.setupEditor,lambda AddCardsObj: runHook("addEditorSetup",AddCardsObj))
AddCards.addCards=wrap(AddCards.addCards,lambda AddCardsObj: runHook("tooltip",AddCardsObj))

# add functions to those hooks
addHook("addEditorSetup",myImport.setupMyMenu)
addHook("unloadProfile",myImport.save)
addHook("tooltip",myImport.myTooltip)
addHook("addHistory",myImport.cardAdded)
