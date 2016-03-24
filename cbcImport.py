#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" cbcImport -- an interface to add notes to Anki on a 
case by case basis. """

# future: add check box skip_added skip_dupes
# future: second Index for all cards

import glob
import copy
from gettext import gettext as _
from aqt import mw  # main window
from aqt.addcards import AddCards  # addCards dialog
from aqt.utils import shortcut, tooltip
# todo: no *
from aqt.qt import *
from anki.hooks import addHook, runHook, wrap
from cbcimport.vocabulary import VocabularyCollection
from cbcimport.util import split_multiple_delims
from cbcimport.log import logger

try:
    from ignore_dupes.ignore_dupes import expression_dupe
except ImportError:
    logger.warning("Couldn't import the ignore_dupes function. Will replace it with a dummy function.")

    def expression_dupe(*args, **kwargs):
        return False

# TODO: FIELDS MORE CLEAR (MULTIPLE USED EXPRESSION ETC.)
# TODO: Laden von Dateinamen an Bauen von Menu koppeln, nicht einfach an Init (da nur bei Start von Anki ausgeführt...) 


class CbcImport(object):
    def __init__(self):
        """ init and basic configuration """
        # todo: move config to config object
        # ----------- BEGIN CONFIG -----------   
        # file to import (change the "..." part)
        # self.importFile=os.path.expanduser("~/Desktop/tangorin_38567.csv")
        # self.importFile=os.path.expanduser('~/Desktop/rest.csv')
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
            import_file_name, import_file_ext = os.path.splitext(self.importFile)
        else:
            import_file_name = None
            import_file_ext = None
        # files where the subset of added/remaining Cards will be Saved
        # (by default: self.importFile - file ending + "added"/"rest" + extension)
        # Note that the file contents will be overwritten!
        # If self.addedFile=None or False or "" is specified
        # no output will be created for addedFile (restFile analogous)
        self.addedFile = None
        self.restFile = os.path.expanduser('~/Desktop/rest.csv')
        # self.addedFile=os.path.expanduser('~/Desktop/added.csv')
        # self.restFile=os.path.expanduser('~/Desktop/rest.csv')
        # self.addedFile=importFileName+"_added"+importFileExt
        # self.restFile=importFileName+"_rest"+importFileExt
        
        self.care_for_dupes = True # Should dupes be treated differently?
        self.create_empty_files = False # Should export files created even if data empty?
        self.default_editor = "leafpad "   # Command to run default editor
                                        # (include space or switch)
        
        # ----------- END CONFIG -----------

        self.data = VocabularyCollection()
        
        self.e = None     # instance of the Editor window
        self.mw = None    # instance of main window
        
        # was last Card added to self.added?
        self.last_added = None  # type: None|bool
        
        self.buttons = {}  # type: dict[str: QPushButton]
        self.status = None  # type: QLabel
        self.status_icons_box = None  # type: QBoxLayout
        self.new_icons_box = None  # type: QBoxLayout

    def wrap(self, note, current):
        """ Updates note $note with data from $current. """
        # ----------- BEGIN CONFIG -----------
        self.delim = unicode('・', self.encoding)

        # TODO: the actual splitting should also be done in the word object; note that this is tangorin specific


        note['Expression'] = current.splitted_expression[0]
        note['Meaning'] = current.formatted_meaning
        # ----------- END CONFIG -----------
        
        return note

    def insert(self):
        """ Inserts an entry from self.queue
        into the Anki Dialog
        """
        if self.data.is_queue_empty():
            tooltip(_("Queue is empty!"), period=1000)
            return
        if not self.data.is_go_next_possible():
            tooltip(_("Was last entry!"), period=1000)
        
        self.clear_all_fields()
        
        current = self.data.get_current()  # source
        note = copy.copy(self.e.note)         # target
        
        self.e.setNote(self.wrap(note, current))
        
        self.run_hooks()
        self.update_status()
    
    def clear_all_fields(self):
        """ Resets all fields. """
        for field in mw.col.models.fieldNames(self.e.note.model()):
            self.e.note[field] = ''
        self.e.note.flush()

    # Loading/Saving file
    # ------------------------

    def new_input_file(self):
        filters = "csv Files (*.csv);;All Files (*)"
        import_file = QFileDialog.getSaveFileName(QFileDialog(), "Pick a file to import.",
                                                  self.defaultDir, filters, options=QFileDialog.DontConfirmOverwrite)
        if import_file:
            self.importFile = import_file
        self.update_status()
    
    def load(self):
        """ Loads input file to self.data. """
        self.data = VocabularyCollection()

        logger.debug("Loading file. ")
        if not self.importFile:
            logger.warning("No import file was specified.")
            tooltip(_("No import file specified"), period=1500)
            return False

        try:
            self.data.load(self.importFile)
        except Exception, e:
            logger.debug("Loading exception: %s, %s.", Exception, e)
            tooltip(_("Could not open input file %s" % self.importFile), period=1500)

        self.update_duplicates()
        self.data.go_first()
        self.update_status()
        tooltip(_("All: %d (Dupe: %d)" % (self.data.len_all(), self.data.len_dupe())), period=1500)

    # todo: the actual work of this should be moved to data_classes
    def update_duplicates(self):
        """ If self.careForDupes==True: updates the duplicate status of all
        entries in the data. Else: does nothing. 
        Return value (bool): Was something changed?"""

        logger.debug("Updating duplicates.")

        if not self.care_for_dupes:
            logger.debug("Ignoring all duplicates.")
            return False
        
        changes = False

        for i in range(len(self.data._data)):
            entry = self.data._data[i]
            logger.debug(u"Checking {}".format(entry["Expression"]))
            if expression_dupe(entry["Expression"]):
                if not entry.is_dupe:
                    changes = True
                entry.is_dupe = True
                # write back!
                self.data._data[i] = entry
                logger.debug("Marked Entry %s as duplicate." % entry["Expression"])
                logger.debug("It's the %dth duplicate." % self.data.len_dupe())

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

    def save_button_pushed(self):
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
            os.system("%s %s &" % (self.default_editor, self.importFile))
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
        self.data.reverse()
        self.update_status()
        
    # Running Hooks and similar
    # -------------------------------------
    
    def run_hooks(self):
        """ Runs the hook 'editFocusLost'. 
        Expl.: A lot of other plugins (e.g. furigana completion etc.) activate as 
        soon as 'editFocusLost' is called (normally triggered after manually 
        editing a field). Calling it directly saves us the trouble of clicking
        into the 'Expression' field and outside again to trigger this.
        """
        changed_fields = ['Expression', 'Meaning']
        for field in changed_fields:
            field_idx = mw.col.models.fieldNames(self.e.note.model()).index(field)
            runHook('editFocusLost', False, self.e.note, field_idx)
        self.e.loadNote()
    
    def card_added(self, obj, note):
        """ This function gets called once a card is added and
        is needed to update self.added (list of added cards)
        """
        self.last_added = False
        # save user input
        # this seems to be neccessary
        note.flush()
        if self.data.is_go_next_possible():
            # current queue Element Expression
            current = self.data.get_current()
            exp = note['Expression']
            # we have to check if the we really are adding an element
            # of the queue. Problem is that we want to allow some tolerance

            # todo: I don't trust this
            if self.data.is_expression_in_queue(exp):
                self.last_added = True
                current.is_added = True
                self.data.set_current(current)

        self.update_status()
        
    def my_tooltip(self, *args):
        """ Has to be called separately to overwrite native
        'Added' tooltip.
        """
        if self.last_added:
            tooltip(_("Added to added"), period=1000)
        else:
            tooltip(_("NOT ADDED TO ADDED!"), period=1000)

    # Setup Menu
    # ----------------------------------------

    def setup_my_menu(self, add_cards_dialogue):
        """ Creates the line of buttons etc. to control this addon. """
        self.e = add_cards_dialogue.editor
        self.mw = add_cards_dialogue.mw
        # adapted from from /usr/share/anki/aqt/editor.py Lines 350
        self.new_icons_box = QHBoxLayout()
        if not isMac:
            self.new_icons_box.setMargin(6)
            self.new_icons_box.setSpacing(0)
        else:
            self.new_icons_box.setMargin(0)
            self.new_icons_box.setSpacing(14)
        self.e.outerLayout.addLayout(self.new_icons_box)
        # Buttons
        # Buttons starting with cbcQ_ are only active if queue is non empty
        # (carefull when changing button name!)
        self.add_my_button("cbc_NewInputFile", [self.new_input_file, self.update_button_states],
                           text="Choose File", tip="Choose new input file.", size="30x120", )
        self.add_my_button("cbc_Load", [self.load, self.update_button_states],
                           text="Load", tip="Load file", size="30x60", )
        self.add_my_button("cbcQ_Show", [self.show, self.update_button_states],
                           text="Show", tip="Show file", size="30x60", )
        self.add_my_button("cbcQ_Reverse", [self.reverse, self.update_button_states],
                           text="Reverse", tip="Reverse Order", size="30x60", )
        self.add_my_button("cbcQ_Save", [self.save_button_pushed, self.update_button_states],
                           text="Save", tip="Saves all added resp. all remaining notes to two files.", size="30x60", )
        self.add_my_button("cbcQ_First", [self.first, self.update_button_states],
                           text="<<", tip="Fill in first entry", size="30x50", )
        self.add_my_button("cbcQ_Previous", [self.previous, self.update_button_states],
                           text="<", tip="Fill in previous entry", size="30x50", )
        self.add_my_button("cbcQ_Fill", [self.insert, self.update_button_states],
                           text="X", tip="Fill in form (Ctrl+F)", size="30x50",
                           key="Ctrl+F")
        self.add_my_button("cbcQ_Next", [self.next, self.update_button_states],
                           text=">", tip="Fill in next entry (Ctrl+G)", size="30x50",
                           key="Ctrl+G")
        self.add_my_button("cbcQ_Last", [self.last, self.update_button_states],
                           text=">>", tip="Fill in last entry", size="30x50", )
        # self.updateButtonStates() # maybe tooltips are better...
        # Status Field
        self.status_icons_box = QHBoxLayout()
        if not isMac:
            self.status_icons_box.setMargin(6)
            self.status_icons_box.setSpacing(0)
        else:
            self.status_icons_box.setMargin(0)
            self.status_icons_box.setSpacing(14)
        self.e.outerLayout.addLayout(self.status_icons_box)
        self.status = QLabel()
        self.update_status()
        self.status_icons_box.addWidget(self.status)
        self.update_button_states()

    def add_my_button(self, name, funcs, key=None, tip=None, size="30x50", text="", check=False):
        """ Shortcut to add a new button to self.new_icons_box.
        :param name: We do self.buttons[name] = button
        :param funcs: List of functions the button should be connected to.
        :param key: ?
        :param tip: Tooltip
        :param size: Either None or of form "30x50" etc.
        :param text: Text of the button
        :param check: Is button checkable?
        :return: button
        """
        # adapted from from /usr/share/anki/aqt/editor.py Lines 308 and following
        b = QPushButton(text)
        # The Focus should still be on the 'Add' button.
        b.setAutoDefault(False)
        b.setDefault(False)
        if check:
            b.setCheckable(True)
            for func in funcs:
                b.connect(b, SIGNAL("clicked(bool)"), func)
        else:
            for func in funcs:
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
        self.new_icons_box.addWidget(b)
        self.buttons[name] = b
        return b

    def update_button_states(self):
        if not self.data.is_queue_empty():
            for buttonName in self.buttons:
                if buttonName.startswith('cbcQ_'):
                    self.buttons[buttonName].setEnabled(True)
        self.buttons["cbcQ_Next"].setEnabled(self.data.is_go_next_possible())
        self.buttons["cbcQ_Last"].setEnabled(self.data.is_go_next_possible())
        self.buttons["cbcQ_Previous"].setEnabled(self.data.is_go_previous_possible())
        self.buttons["cbcQ_First"].setEnabled(self.data.is_go_previous_possible())
        if self.data.is_queue_empty():
            for buttonName in self.buttons:
                if buttonName.startswith('cbcQ_'):
                    self.buttons[buttonName].setEnabled(False)

    def update_status(self):
        """ Updates button texts e.g. to display
        number of remaining entries etc.
        """
        def shorten(string, length=10):
            """ Cuts off beginning string so that only $mlen characters remain and
            adds '...' at the front if nescessary.
            :type length: int
            :type string: str
            """
            if len(string) <= length:
                return string
            else:
                return "..." + string[-length:]

        def format_key_value(key, value):
            return "<b>{}:</b> {}".format(key, red(value))

        def red(string):
            return '<font color="red">{}</font>'.format(string)

        def format_bool_html(value):
            if value is False:
                fcolor = "White"
                bcolor = "Red"
            elif value is True:
                fcolor = "White"
                bcolor = "Green"
            else:
                # no formatting
                return value
            return """<span style="background-color: %s; color: %s">%s</span>""" % (bcolor, fcolor, str(value))

        divider = "<big>|</big>"
        texts = [format_key_value("In", shorten(self.importFile, length=20)),
                 divider,
                 format_key_value("Cur", "{}/{}".format(self.data.reduced_cursor(), self.data.len_queue())),
                 format_key_value("Idx", "{}/{}".format(self.data.full_cursor(), self.data.len_all())),
                 divider,
                 format_key_value("Add", self.data.len_added()),
                 format_key_value("Dup", self.data.len_dupe()),
                 format_key_value("Black", self.data.len_black()),
                 divider,
                 "<b>LA</b>: {}".format(format_bool_html(self.last_added)),
                 ]

        self.status.setText('&nbsp;&nbsp;'.join(texts))


myImport = CbcImport()

# generate new hooks
AddCards.addHistory = wrap(AddCards.addHistory, lambda *args: runHook("addHistory", *args))
AddCards.setupEditor = wrap(AddCards.setupEditor, lambda add_cards_obj: runHook("addEditorSetup", add_cards_obj))
AddCards.addCards = wrap(AddCards.addCards, lambda add_cards_obj: runHook("tooltip", add_cards_obj))

# add functions to those hooks
addHook("addEditorSetup", myImport.setup_my_menu)
addHook("unloadProfile", myImport.save)
addHook("tooltip", myImport.my_tooltip)
addHook("addHistory", myImport.card_added)
