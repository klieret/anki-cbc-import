#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" cbcImport -- an interface to add notes to Anki on a
case by case basis. """

# future: add check box skip_added skip_dupes, skip_black, skip_normal

import glob
import copy
from gettext import gettext as _
from aqt import mw  # main window
from aqt.utils import shortcut, tooltip
import os.path
from aqt.qt import QFileDialog, QHBoxLayout, isMac, QPushButton, QLabel, SIGNAL, QIcon, QKeySequence, QBoxLayout, \
    QCheckBox, QSpacerItem, QVBoxLayout, QFrame
from anki.hooks import runHook
from cbcimport.vocabulary import VocabularyCollection
from cbcimport.log import logger
from config import config


class CbcImportUi(object):
    def __init__(self):
        """ init and basic configuration """
        self.default_dir = os.path.expanduser(config.get("general", "default_dir"))
        self.import_file = None  # type: str
        self.added_file = None  # type: str
        self.rest_file = None  # type: str

        # todo: implement with config
        # todo: use Process module to launch in its own thread
        self.default_editor = "leafpad {filename} &"   # Command to run default editor (include space or switch)

        # Note that nothing is added yet.
        self.data = VocabularyCollection()

        self.e = None     # instance of the Editor window
        self.mw = None    # instance of main window

        # was last Card added to self.added?
        self.last_added = None  # type: None|bool

        # Qt objects:
        self.frame = None  # type: QFrame
        self.cbc_box = None  # type: QBoxLayout
        self.buttons = {}  # type: dict[str: QPushButton]
        self.checkboxes = {}  # type: dict[str: QCheckBox]
        self.status = None  # type: QLabel
        self.status_box = None  # type: QBoxLayout
        self.button_box = None  # type: QBoxLayout
        self.settings_box = None  # type: QBoxLayout

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

        current = self.data.get_current()
        note = copy.copy(self.e.note)
        note['Expression'] = current.splitted_expression[0]
        note['Meaning'] = current.formatted_meaning

        self.e.setNote(note)
        self.run_hooks()
        self.update_status()

    def clear_all_fields(self):
        """ Resets all fields. """
        for field in mw.col.models.fieldNames(self.e.note.model()):
            self.e.note[field] = ""
        self.e.note.flush()

    # Loading/Saving file
    # ------------------------

    def new_input_file(self):
        filters = "csv Files (*.csv);;All Files (*)"
        import_file = QFileDialog.getSaveFileName(QFileDialog(), "Pick a file to import.",
                                                  self.default_dir, filters, options=QFileDialog.DontConfirmOverwrite)
        if import_file:
            self.import_file = import_file
        self.update_status()

    def load(self):
        """ Loads input file to self.data. """
        self.data = VocabularyCollection()

        logger.debug("Loading file. ")
        if not self.import_file:
            logger.warning("No import file was specified.")
            tooltip(_("No import file specified"), period=1500)
            return False

        try:
            self.data.load(self.import_file)
        except Exception, e:
            logger.debug("Loading exception: %s, %s.", Exception, e)
            tooltip(_("Could not open input file %s" % self.import_file), period=1500)

        self.data.go_first()
        self.update_status()
        tooltip(_("All: %d (Dupe: %d)" % (self.data.len_all(), self.data.len_dupe())), period=1500)

    def save(self):
        """ Saves self.added and self.rest to the resp. files """
        pass

        # todo

        # if self.added_file and (self.createEmptyFiles or len(self.added)>0):
        #     try:
        #         with open(self.added_file,'wb') as csvfile:
        #             writer=csv.writer(csvfile, delimiter=self.delim)
        #             for row in self.added:
        #                 row=[c.encode(self.encoding) for c in row]
        #                 writer.writerow(row)
        #     except:
        #         tooltip(_("Could not open output file %s" % self.added_file),period=1500)

        # if self.rest_file and (self.createEmptyFiles or len(self.rest)>0):
        #     try:
        #         with open(self.rest_file,'wb') as csvfile:
        #             writer=csv.writer(csvfile, delimiter=self.delim)
        #             for row in self.rest:
        #                 row=[c.encode(self.encoding) for c in row]
        #                 writer.writerow(row)
        #     except:
        #         tooltip(_("Could not open output file %s" % self.rest_file),period=1500)

    def save_button_pushed(self):
        """ What happens if save button is pushed:
        Show tooltip and save."""
        self.save()
        # # tooltip
        # text=""
        # if self.added_file:
        #     text+="Saved added "
        # if self.rest_file:
        #     text+="Saved rest"
        # if text=="":
        #     text+="NO FILE TO SAVE"
        # tooltip(_(text), period=1500)

    def show(self):
        """ Opens input file in an external editor. """
        if self.import_file.strip():
            os.system(self.default_editor.format(filename=self.import_file))
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

    # noinspection PyUnusedLocal
    def on_add_history(self, obj, note):
        """ This function gets called once a card is added and
        is needed to update self.added (list of added cards).
        :param obj: ? (we need this since this is called via hook)
        :param note: The note that was just added.
        """
        self.last_added = False
        # save user input
        # this seems to be neccessary
        note.flush()
        if self.data.is_go_next_possible():
            # We have to check if the we really are adding an element
            # of the queue. Problem is that we want to allow some tolerance
            if self.data.is_expression_in_queue(note['Expression']):
                self.last_added = True
                self.data.get_current().is_added = True

        self.update_status()

    # noinspection PyUnusedLocal
    def on_cards_added(self, *args):
        """ Has to be called separately to overwrite native 'Added' tooltip.
        """
        if self.last_added:
            tooltip(_("Added to added"), period=1000)
        else:
            tooltip(_("NOT ADDED TO ADDED!"), period=1000)

    def on_editor_opened(self, editor):
        """ Gets called when the user opens the edit dialog.
        :param editor: The edit dialog.
        """
        # We do the setup of the links for the files here because else we wouldn't
        # find files that have been added after Anki has been started.
        try:
            # last file of all files that are on Desktop and have extension .csv
            self.import_file = glob.glob(os.path.expanduser("~/Desktop/*.csv"))[-1]
        except IndexError:
            self.import_file = None
        self.rest_file = os.path.expanduser('~/Desktop/rest.csv')

        self.setup_my_menu(editor)

    def setup_my_menu(self, editor):
        """ Creates the line of buttons etc. to control this addon.
        :param editor
        """
        self.e = editor.editor
        self.mw = editor.mw

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Box)
        self.frame.setFrameShadow(QFrame.Sunken)
        self.cbc_box = QVBoxLayout(self.frame)
        self.e.outerLayout.addWidget(self.frame)

        self.button_box = QHBoxLayout()
        self.status_box = QHBoxLayout()
        self.settings_box = QHBoxLayout()

        # adapted from from /usr/share/anki/aqt/editor.py Lines 350
        for box in [self.cbc_box]:
            if not isMac:
                box.setMargin(6)
                box.setSpacing(0)

            else:
                box.setMargin(0)
                box.setSpacing(14)

        self.cbc_box.addLayout(self.button_box)
        self.cbc_box.addLayout(self.status_box)
        self.cbc_box.addLayout(self.settings_box)

        # Buttons starting with cbcQ_ are only active if queue is non empty
        # (carefull when changing button name!)
        self.add_button("cbc_NewInputFile", [self.new_input_file, self.update_enabled_disabled],
                        text="Choose File", tip="Choose new input file.", size="30x120", )
        self.add_button("cbc_Load", [self.load, self.update_enabled_disabled],
                        text="Load", tip="Load file", size="30x60", )
        self.add_button("cbcQ_Show", [self.show, self.update_enabled_disabled],
                        text="Show", tip="Show file", size="30x60", )
        self.add_button("cbcQ_Reverse", [self.reverse, self.update_enabled_disabled],
                        text="Reverse", tip="Reverse Order", size="30x60", )
        self.add_button("cbcQ_Save", [self.save_button_pushed, self.update_enabled_disabled],
                        text="Save", tip="Saves all added resp. all remaining notes to two files.", size="30x60", )
        self.add_button("cbcQ_First", [self.first, self.update_enabled_disabled],
                        text="<<", tip="Fill in first entry", size="30x50", )
        self.add_button("cbcQ_Previous", [self.previous, self.update_enabled_disabled],
                        text="<", tip="Fill in previous entry", size="30x50", )
        self.add_button("cbcQ_Fill", [self.insert, self.update_enabled_disabled],
                        text="X", tip="Fill in form (Ctrl+F)", size="30x50",
                        key="Ctrl+F")
        self.add_button("cbcQ_Next", [self.next, self.update_enabled_disabled],
                        text=">", tip="Fill in next entry (Ctrl+G)", size="30x50",
                        key="Ctrl+G")
        self.add_button("cbcQ_Last", [self.last, self.update_enabled_disabled],
                        text=">>", tip="Fill in last entry", size="30x50", )

        self.add_checkbox("cbcQ_skip_dupe", [self.on_checkbox_changed], "Skip Dupe")
        self.add_checkbox("cbcQ_skip_added", [self.on_checkbox_changed], "Skip Added")
        self.add_checkbox("cbcQ_skip_black", [self.on_checkbox_changed], "Skip Black")
        self.add_checkbox("cbcQ_skip_rest", [self.on_checkbox_changed], "Skip Rest")

        self.status = QLabel()
        self.update_status()
        self.status_box.addWidget(self.status)

        self.update_enabled_disabled()
        self.on_checkbox_changed()

    def on_checkbox_changed(self):
        print "on checkbox changed"
        self.data.dupes_in_queue = not self.checkboxes["cbcQ_skip_dupe"].isChecked()
        self.data.added_in_queue = not self.checkboxes["cbcQ_skip_added"].isChecked()
        self.data.blacklisted_in_queue = not self.checkboxes["cbcQ_skip_black"].isChecked()
        self.data.rest_in_queue = not self.checkboxes["cbcQ_skip_rest"].isChecked()
        self.update_status()
        self.update_enabled_disabled()

    def add_checkbox(self, name, funcs, text):
        checkbox = QCheckBox()
        checkbox.adjustSize()
        checkbox.setText(text)
        checkbox.adjustSize()
        self.settings_box.addWidget(checkbox)
        self.checkboxes[name] = checkbox
        for func in funcs:
            checkbox.connect(checkbox, SIGNAL("clicked(bool)"), func)
        return checkbox

    def add_button(self, name, funcs, key=None, tip=None, size="30x50", text="", check=False):
        """ Shortcut to add a new button to self.button_box.
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
        button = QPushButton(text)

        # The Focus should still be on the 'Add' button.
        button.setAutoDefault(False)
        button.setDefault(False)

        if check:
            button.setCheckable(True)
            for func in funcs:
                button.connect(button, SIGNAL("clicked(bool)"), func)
        else:
            for func in funcs:
                button.connect(button, SIGNAL("clicked()"), func)

        if size:
            if size.split('x')[0]:
                button.setFixedHeight(int(size.split('x')[0]))
            button.setFixedWidth(int(size.split('x')[1]))

        if not text:
            button.setIcon(QIcon(":/icons/%s.png" % name))

        if key:
            button.setShortcut(QKeySequence(key))

        if tip:
            button.setToolTip(shortcut(tip))

        self.button_box.addWidget(button)
        self.buttons[name] = button
        return button

    def update_enabled_disabled(self):
        if not self.data.is_queue_empty():
            for buttonName in self.buttons:
                if buttonName.startswith('cbcQ_'):
                    self.buttons[buttonName].setEnabled(True)
            for checkboxName in self.checkboxes:
                if checkboxName.startswith('cbcQ_'):
                    self.checkboxes[checkboxName].setEnabled(True)
        self.buttons["cbcQ_Next"].setEnabled(self.data.is_go_next_possible())
        self.buttons["cbcQ_Last"].setEnabled(self.data.is_go_next_possible())
        self.buttons["cbcQ_Previous"].setEnabled(self.data.is_go_previous_possible())
        self.buttons["cbcQ_First"].setEnabled(self.data.is_go_previous_possible())
        if self.data.is_queue_empty():
            for buttonName in self.buttons:
                if buttonName.startswith('cbcQ_'):
                    self.buttons[buttonName].setEnabled(False)
            for checkboxName in self.checkboxes:
                if checkboxName.startswith('cbcQ_'):
                    self.checkboxes[checkboxName].setEnabled(False)

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
        texts = [format_key_value("In", shorten(self.import_file, length=20)),
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
