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
	def load(self):
		""" Loads self.importFile to self.data. """
		self.data=[]
		with open(self.importFile,'r') as csvfile:
			reader=csv.reader(csvfile, delimiter="\t")
			for row in reader:
				self.data.append(row)
	def clean(self,a):
		""" Resets all fields. """
		for field in mw.col.models.fieldNames(a.note.model()):
			a.note[field]=''
		a.note.flush()
	def next(self,a):
		""" Inserts next Entry. """
		if self.currentIdx<len(self.data)-1:
			self.currentIdx+=1
		self.insert(a)
	def previous(self,a):
		""" Inserts previous Entry. """
		if self.currentIdx>=1:
			self.currentIdx-=1
		self.insert(a)
	def insert(self,a):
		""" Inserts current Entry. """
		self.clean(a)
		if not self.currentIdx < len(self.data):
			# should only happen if data could not
			# be imported.
			return
		current=self.data[self.currentIdx]
		# ADAPT this!
		# ---------------
		a.note['Expression']=unicode(current[0].split('・')[-1],'utf-8')
		a.note['Meaning']=unicode(current[2],'utf-8')
		# ---------------
		a.note.flush()
		a.loadNote()
		self.runHooks(a)
	def runHooks(self,a)
		""" Calls 'editFocusLost'. """
		# A lot of other plugins (e.g. furigana completion etc.) run as 
		# soon as 'editFocusLost' is called (normally called after manually 
		# editing a field). Calling it directly saves us the trouble of clicking
		# into the 'Expression' field and outside again to trigger this.
		f=mw.col.models.fieldNames(a.note.model()).index('Expression')
		runHook('editFocusLost',False,a.note,f)
		a.loadNote()
	
	def mySetupButtons(self,a):
		""" Setup Buttons. """
		a._addButton("mybutton", lambda: self.load(), text="Load", size=False)
		a._addButton("mybutton", lambda: self.insert(a), text="Fill", size=False, key="Ctrl+F")
		a._addButton("mybutton", lambda: self.next(a), text="+", size=False, key="Ctrl+G")
		a._addButton("mybutton", lambda: self.previous(a), text="-", size=False, key="Ctrl+H")
	

a=cbcImport()
Editor.setupButtons = wrap(Editor.setupButtons, a.mySetupButtons)

