#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aqt import mw
from anki.hooks import addHook, runHook
from aqt import addcards
from anki.hooks import wrap
from aqt.editor import Editor
import csv
import os.path
from aqt.utils import shortcut
from aqt.qt import *

class cbcImport():
	def __init__(self):
		""" init """
		# file to import
		self.importFile=os.path.expanduser("~/Desktop/tangorin_38567.csv")
		# data from import File will be saved in self.data:
		self.data=[] # format: [(field1,field2,...)]
		# how many of the vocabulary have we already added:
		self.currentIdx=0
		# saves the instance of the Editor window
		self.e=None
		self._buttons={}
	def load(self):
		""" Loads self.importFile to self.data. """
		self.data=[]
		with open(self.importFile,'r') as csvfile:
			reader=csv.reader(csvfile, delimiter="\t")
			for row in reader:
				self.data.append(row)
		self.updateStatus()
	def clean(self):
		""" Resets all fields. """
		for field in mw.col.models.fieldNames(self.e.note.model()):
			self.e.note[field]=''
		self.e.note.flush()
	def last(self):
		""" Inserts last Entry. """
		self.currentIdx=len(self.data)-1
		self.insert()
	def next(self):
		""" Inserts next Entry. """
		if self.currentIdx<len(self.data)-1:
			self.currentIdx+=1
		self.insert()
	def previous(self):
		""" Inserts previous Entry. """
		if self.currentIdx>=1:
			self.currentIdx-=1
	def first(self):
		self.currentIdx=0
		self.insert()
	def insert(self):
		""" Inserts current Entry. """
		self.clean()
		if not self.currentIdx < len(self.data):
			# should only happen if data could not
			# be imported.
			return
		current=self.data[self.currentIdx]
		# ADAPT this!
		# ---------------
		self.e.note['Expression']=unicode(current[0].split('・')[-1],'utf-8')
		self.e.note['Meaning']=unicode(current[2],'utf-8')
		# ---------------
		self.e.note.flush()
		self.e.loadNote()
		self.runHooks()
		self.updateStatus()
	def runHooks(self):
		""" Calls 'editFocusLost'. 
		 Expl.: A lot of other plugins (e.g. furigana completion etc.) run as 
		soon as 'editFocusLost' is called (normally called after manually 
		editing a field). Calling it directly saves us the trouble of clicking
		into the 'Expression' field and outside again to trigger this. """
		f=mw.col.models.fieldNames(self.e.note.model()).index('Expression')
		runHook('editFocusLost',False,self.e.note,f)
		self.e.loadNote()
	
	def mySetupButtons(self,editor):
		self.e=editor
		# adapted from from /usr/share/anki/aqt/editor.py Lines 350
		self.newIconsBox = QHBoxLayout()
		if not isMac:
			self.newIconsBox.setMargin(6)
			self.newIconsBox.setSpacing(0)
		else:
			self.newIconsBox.setMargin(0)
			self.newIconsBox.setSpacing(14)
		self.e.outerLayout.addLayout(self.newIconsBox)
		# --
		self.myAddButton("cbcLoad", self.load, text="Load", tip="Load file", size=False, )
		self.myAddButton("cbcFirst", self.first, text="<<", tip="Fill in first entry", size=False,)
		self.myAddButton("cbcPrevious", self.previous, text="<", tip="Fill in previous entry", size=False , key="Ctrl+H")
		self.myAddButton("cbcFill", self.insert, text="X", tip="Fill in form", size=False,  key="Ctrl+F")
		self.myAddButton("cbcNext", self.next, text=">", tip="Fill in next entry", size=False, key="Ctrl+G")
		self.myAddButton("cbcLast", self.last, text=">>", tip="Fill in last entry", size=False , )
		self.status=QLabel()
		self.newIconsBox.addWidget(self.status)
		
	def myAddButton(self, name, func, key=None, tip=None, size=True, text="", check=False):
		# adapted from from /usr/share/anki/aqt/editor.py Lines 308..
		b = QPushButton(text)
		if check:
			b.connect(b, SIGNAL("clicked(bool)"), func)
		else:
			b.connect(b, SIGNAL("clicked()"), func)
		if size:
			b.setFixedHeight(20)
			b.setFixedWidth(60)
		if not text:
			b.setIcon(QIcon(":/icons/%s.png" % name))
		if key:
			b.setShortcut(QKeySequence(key))
		if tip:
			b.setToolTip(shortcut(tip))
		if check:
			b.setCheckable(True)
		self.newIconsBox.addWidget(b)
		# change: always add buttons
		self._buttons[name] = b
		return b
	
	def updateStatus(self):
		""" Updates button texts e.g. to display 
		number of remaining entries etc. """
		if not len(self.data)==0:
			self.status.setText("%d/%d" % (self.currentIdx+1,len(self.data)))	
		

myImport=cbcImport()
Editor.setupButtons = wrap(Editor.setupButtons, myImport.mySetupButtons)

