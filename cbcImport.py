#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from aqt import mw # main window
# from aqt.editor import Editor
# from aqt.addcards import AddCards # addCards dialog
# from aqt.utils import shortcut, tooltip, getSaveFile
# from aqt.qt import *

# from anki.hooks import addHook, runHook, wrap

# from ignore_dupes import expressionDupe

import csv
# import os.path
# import glob
# import copy
# import os


# TODO: FIELDS MORE CLEAR (MULTIPLE USED EXPRESSION ETC.)
# TODO: neue Base
# TODO: Laden von Dateinamen an Bauen von Menu koppeln, nicht einfach an Init (da nur bei Start von Anki ausgeführt...) 
# TODO: keine Checks etc., wenn noch nicht mal mehr Datei geladen.
# TODO: Button zum entladen von Datein
# Problem: Curser bleibt stehen, wenn jetzt QUEUE verkürzt wird
# evtl. curser out of range?

# 1. RESTART ANKI AFTER EACH EDIT (ELSE IT WON'T TAKE EFFECT)
# 2. NOTE THAT IDENTATION MATTERS IN PYTHON. 
# 3. DON'T USE SPACES TO INDENT IN THIS FILE.

class dataElement(object):
	def __init__(self):
		# The fields that are to be synchronized with 
		# the anki note
		# should be of type 
		# "fieldname":"value"
		self.fields = {}

		self.isDupe = False
		self.isAdded = False

	def isInQueue(self):
		return not self.isDupe and not self.isAdded

	def setFieldsHook(self):
		pass

class dataSet(object):
	def __init__(self):

		self._data = []

		# which element are we looking at 
		# right now
		self._cursor = 0

	def getCurrent(self):
		return self._data[self._cursor]

	def load(self, filename):
		""" Loads input file to self._data. """
		with open(filename,'r') as csvfile:
			reader = csv.reader(csvfile, delimiter='\t')
			for row in reader:
				element = dataElement()
				
				fields = [c.decode('utf8') for c in row]

				# must match Anki fieldnames. If you want to ignore a field, just set it to ""
				fieldNames = ["Expression", "Kana", "Translation", ""]
				
				if not len(fields) == len(fieldNames):
					raise ValueError, "The number of supplied fieldNames (%d) doesn't match the number of fields in the file %s (%d)." % (len(fieldNames), filename, len(fields))
				
				for i in range(len(fields)):
					element.fields[fieldNames[i]] = fields[i] 
				
				element.setFieldsHook()
				self._data.append(element)

	# Navigate with skipping.

	def go(self, func, start = None):
		""" Updates self._cursor. 
		Starts with cursor = $start (default: self.cursor)
		and repeatedly call cursor = fun(cursor).
		Once the element at cursor is an element that should be in 
		the queue, we set self._cursor = cursor.
		Returns True if self._cursor was changed, False otherwise. """
	 	
		if not start:
			start = self._cursor

	 	cursor = start
		oldCursor = self._cursor
		cursor = func(cursor)	
		
		while cursor in range(len(dataElements)):
			if dataElements[cursor].isInQueue:
				self._cusor = cursor
				break 
			cursor = func(cursor)	
		
		return oldCursor == self._cursor

	def goNext(self):
		""" Go to next queue element 
		(i.e. sets self._cursor to the index of the next queue element)
		Returns False if we are already at the last queue element. """
		return self.go(lambda x: x+1)

	def goPrevious(self):
		""" Go to previous queue element 
		(i.e. sets self._cursor to the index of the previous queue element)
		Returns False if we are already at the first queue element. """

	 	return self.go(lambda x: x-1)

	def goFirst(self):
		return self.go(lambda x: x+1, start = 0)
		""" Go to first queue element 
		(i.e. sets self._cursor to the index of the first queue element)
		Returns False if we are already at the first queue element. """
		
	def goLast(self):
	 	""" Go to last queue element 
		(i.e. sets self._cursor to the index of the last queue element)
		Returns False if we are already at the last queue element. """
		
	 	return self.go(lambda x: x-1, start = len(self._cursor))


class cbcImport():
	def __init__(self):
		""" init and basic configuration """
		# ----------- BEGIN CONFIG -----------
		
		# file to import (change the "..." part)
		#self.importFile=os.path.expanduser("~/Desktop/tangorin_38567.csv")
		#self.importFile=os.path.expanduser('~/Desktop/rest.csv')
		self.defaultDir=os.path.expanduser("~/Desktop/")
		try:
			self.importFile=glob.glob(os.path.expanduser("~/Desktop/*.csv"))[-1] # last file of all files that are on Desktop and have extension .csv
		except:
			self.importFile=None
		# delimiter of the input file (character that separates
		# different rows). E.g. '\t' for Tabulator, ';' for ; etc. 
		self.delim='\t'
		
		# character encoding to be used for input and output
		self.encoding='utf-8'
		if self.importFile:
			importFileName,importFileExt=os.path.splitext(self.importFile)
		else:
			importFileName=None
			importFileExt=None
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
		self.createEmptyFiles=False # Should export files created even if data empty?
		self.defaultEditor="leafpad " 	# Command to run default editor 
										# (include space or switch)
		
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
		self.delim=unicode('・',self.encoding)
		# TODO splitting as separate method
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
		note['Expression']=current[0].split(self.delim)[-1] # todo: do we really want that?
		note['Meaning']=enum(current[2])
		# ----------- END CONFIG -----------
		
		return note

	def insert(self):
		""" Inserts an entry from self.queue
		into the Anki Dialog """

		if len(self.queue)==0:
			tooltip(_("Queue is empty!"),period=1000)
			return
		elif not self.currentIdx < len(self.queue):
			tooltip(_("Was last entry!"),period=1000)
			self.currentIdx=len(self.queue)-1
		
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
		filters = "csv Files (*.csv);;All Files (*)"
		importFile=QFileDialog.getSaveFileName(None, "Pick a file to import.", self.defaultDir, filters, options=QFileDialog.DontConfirmOverwrite)
		if importFile:
			self.importFile=importFile
		self.updateStatus()
	
	def load(self):
		""" Loads input file to self.data. """
		# initialize self.data
		self.currentIdx=0 
		self.added=[]
		self.rest=[]
		self.data=[]
		self.queue=[]
		self.dupe=[]
		if not self.importFile:
			tooltip(_("No import file specified"),period=1500)
		try:
			with open(self.importFile,'r') as csvfile:
				reader=csv.reader(csvfile, delimiter=self.delim)
				for row in reader:
					self.data.append([c.decode(self.encoding) for c in row])
		except:
			tooltip(_("Could not open input file %s" % self.importFile),period=1500)
		# initialize subsets
		self.added=[]
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
		for item in self.data:
			delim='・'.decode('utf-8')  # NOT self.encoding!
			exp=item[0].split(delim)[-1]
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
		if self.addedFile and (self.createEmptyFiles or len(self.added)>0):
			try:
				with open(self.addedFile,'wb') as csvfile:
					writer=csv.writer(csvfile, delimiter=self.delim)
					for row in self.added:
						row=[c.encode(self.encoding) for c in row]
						writer.writerow(row)
			except:
				tooltip(_("Could not open output file %s" % self.addedFile),period=1500)
				
		if self.restFile and (self.createEmptyFiles or len(self.rest)>0):
			try:
				with open(self.restFile,'wb') as csvfile:
					writer=csv.writer(csvfile, delimiter=self.delim)
					for row in self.rest:
						row=[c.encode(self.encoding) for c in row]
						writer.writerow(row)
			except:
				tooltip(_("Could not open output file %s" % self.restFile),period=1500)

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

	def show(self):
		if self.importFile:
			os.system("%s %s &" % (self.defaultEditor, self.importFile))
		else:
			tooltip(_("No input File!"), period=1500)
	
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
		""" This function gets called once a card is added and
		is needed to update self.added (list of added cards) """
		self.lastAdded=False
		# save user input
		# this seems to be neccessary
		note.flush()
		if len(self.queue)>self.currentIdx:
			# current queue Element Expression
			current=self.queue[self.currentIdx]
			exp=note['Expression']
			# we have to check if the we really are adding an element
			# of the queue. Problem is that we want to allow some tolerance
			isque=False
			if len(exp)>=3: 
				if exp in current[0]:
					isque=True
			else:
				print(exp,current[0],exp==current[0].split(self.delim)[-1])
				if exp==current[0].split(self.delim)[-1]:
					isque=True
			if isque:
				self.lastAdded=True
				self.added.append(current)
				# FIXME: What if other mode?
				# dupes are not in self.rest
				# also remove from queue!
				self.rest.remove(current)
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




# myImport=cbcImport()

# # generate new hooks
# AddCards.addHistory=wrap(AddCards.addHistory,lambda *args: runHook("addHistory",*args))
# AddCards.setupEditor=wrap(AddCards.setupEditor,lambda AddCardsObj: runHook("addEditorSetup",AddCardsObj))
# AddCards.addCards=wrap(AddCards.addCards,lambda AddCardsObj: runHook("tooltip",AddCardsObj))

# # add functions to those hooks
# addHook("addEditorSetup",myImport.setupMyMenu)
# addHook("unloadProfile",myImport.save)
# addHook("tooltip",myImport.myTooltip)
# addHook("addHistory",myImport.cardAdded)

ds = dataSet()
ds.load("tan.csv")
print(ds._data)