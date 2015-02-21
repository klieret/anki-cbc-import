#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aqt import mw
from anki.hooks import addHook, runHook
from aqt import addcards
from anki.hooks import wrap
from aqt.editor import Editor
import csv
import os.path

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
	def load(self):
		""" Loads self.importFile to self.data. """
		self.data=[]
		with open(self.importFile,'r') as csvfile:
			reader=csv.reader(csvfile, delimiter="\t")
			for row in reader:
				self.data.append(row)
	def clean(self):
		""" Resets all fields. """
		for field in mw.col.models.fieldNames(self.e.note.model()):
			self.e.note[field]=''
		a.note.flush()
	def next(self):
		""" Inserts next Entry. """
		if self.currentIdx<len(self.data)-1:
			self.currentIdx+=1
		self.insert()
	def previous(self):
		""" Inserts previous Entry. """
		if self.currentIdx>=1:
			self.currentIdx-=1
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
	def runHooks(self):
		""" Calls 'editFocusLost'. 
		 Expl.: A lot of other plugins (e.g. furigana completion etc.) run as 
		soon as 'editFocusLost' is called (normally called after manually 
		editing a field). Calling it directly saves us the trouble of clicking
		into the 'Expression' field and outside again to trigger this. """
		f=mw.col.models.fieldNames(self.e.note.model()).index('Expression')
		runHook('editFocusLost',False,a.note,f)
		self.e.loadNote()
	
	def mySetupButtons(self,editor):
		""" Setup Buttons. """
		self.e=editor
		self.e._addButton("cbcLoad", self.load, text="Load", tip="Load file", size=False, canDisable=False, )
		self.e._addButton("cbcFill", self.insert, text="X", tip="Fill in form", size=False, canDisable=False, key="Ctrl+F")
		self.e._addButton("cbcNext", self.next, text=">", tip="Fill in next entry", size=False, canDisable=False, key="Ctrl+G")
		self.e._addButton("cbcPrevious", self.previous, text="<", tip="Fill in previous entry", size=False, canDisable=False, key="Ctrl+H")
	
	def updateButtons(self,a):
		""" Updates button texts e.g. to display 
		number of remaining entries etc. """
		pass
		

myImport=cbcImport()
Editor.setupButtons = wrap(Editor.setupButtons, myImport.mySetupButtons)

