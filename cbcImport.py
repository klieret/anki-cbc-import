#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aqt import mw
from anki.hooks import addHook, runHook
from aqt import addcards
from anki.hooks import wrap
from aqt.editor import Editor
import csv
import os.path
import urllib2

class customAdd():
	def __init__(self):
		self.importFile=os.path.expanduser("~/Desktop/tangorin_38567.csv")
		self.data=[]
		self.currentIdx=0
	def next(self,a):
		if self.currentIdx<len(self.data)-1:
			self.currentIdx+=1
		self.fill(a)
	def previous(self,a):
		if self.currentIdx>=1:
			self.currentIdx-=1
		self.fill(a)
	def clean(self,a):
		for field in mw.col.models.fieldNames(a.note.model()):
			a.note[field]=''
		a.note.flush()
	def load(self):
		self.data=[]
		with open(self.importFile,'r') as csvfile:
			reader=csv.reader(csvfile, delimiter="\t")
			for row in reader:
				self.data.append(row)
	def mySetupButtons(self,a):
		a._addButton("mybutton", lambda: self.load(), text="Load", size=False)
		a._addButton("mybutton", lambda: self.fill(a), text="Fill", size=False, key="Ctrl+F")
		a._addButton("mybutton", lambda: self.next(a), text="+", size=False, key="Ctrl+G")
		a._addButton("mybutton", lambda: self.previous(a), text="-", size=False, key="Ctrl+H")
	def fill(self,a):
		self.clean(a)
		if not self.currentIdx < len(self.data):
			return
		data=self.data[self.currentIdx]
		print(data)
		a.note['Expression']=unicode(data[0].split('・')[-1],'utf-8')
		a.note['Meaning']=unicode(data[2],'utf-8')
		a.note.flush()
		a.loadNote()
		f=mw.col.models.fieldNames(a.note.model()).index('Expression')
		runHook('editFocusLost',False,a.note,f)
		a.loadNote()


a=customAdd()
Editor.setupButtons = wrap(Editor.setupButtons, a.mySetupButtons)

