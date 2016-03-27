#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" The user interface added to Anki's edit dialogues.
"""

import glob
import copy
from anki.lang import _ 
from aqt import mw  # main window
from aqt.utils import shortcut, tooltip
from aqt.qt import *
import aqt
from anki.hooks import runHook
from cbcimport.vocabulary import VocabularyCollection
from cbcimport.log import logger
from config import config as _config  # '_' because CbcImportUi.config should be used after setting it to _config
from ConfigParser import NoOptionError, NoSectionError
from cbcimport.util import layout_widgets

__author__ = "ch4noyu"
__email__ = "ch4noyu@yahoo.com"
__license__ = "LGPLv3"


# fixme: still active, even if we're adding other cards. Causes errors!
# fixme: some of the checkbox states apparently are not saved
# fixme: add function CbcImportUi.is_active() and check it before trying to run hook on close edit dialog.
# todo: save show/hide option
# todo: add an option to hide the options.
# todo: implement blacklist
class CbcImportUi(object):
    def __init__(self):
        """ init and basic configuration """
        self.config = _config
        self.default_dir = os.path.expanduser(self.config.get("general", "default_dir"))

        # will be set in self.on_editor_opened (since we might want to get the content
        # self.default_dir to choose default_pics, and the content might have changed after
        # anki was started.
        self.filename_import = ""  # type: str
        self.filename_added = ""  # type: str
        self.filename_rest = ""  # type: str
        self.filename_black = ""  # type: str

        # todo: implement with config
        # todo: use Process module to launch in its own thread
        self.default_editor = "leafpad {filename} &"   # Command to run default editor (include space or switch)

        # Note that nothing is added yet.
        self.data = VocabularyCollection()

        self.e = None  # instance of the Editor window
        self.mw = None  # instance of main window

        # was last Card added to self.added?
        self.last_added = None  # type: None|bool

        self.hiding = False  # type: bool

        # Qt objects:
        self.frame = None  # type: QFrame
        self.cbc_box = None  # type: QBoxLayout
        self.buttons = {}  # type: dict[str: QPushButton]
        self.checkboxes = {}  # type: dict[str: QCheckBox]
        self.status = None  # type: QLabel
        self.status_box = None  # type: QBoxLayout
        self.button_box = None  # type: QBoxLayout
        self.settings_box = None  # type: QBoxLayout

    # ========================= [ Manipulate notes ] =========================

    def insert(self):
        """ Inserts the current entry from the queue into the Anki editor window"""
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

    # ========================= [ Loading/Saving/Showing files ] =========================

    # todo: should also take black files in consideration!
    def load(self):
        """ Loads input file to self.data. """
        self.data = VocabularyCollection()

        logger.debug("Loading file. ")
        if not self.filename_import:
            logger.warning("No import file was specified.")
            tooltip(_("No import file specified"), period=1500)
            return False

        try:
            self.data.load(self.filename_import)
        except Exception, e:
            logger.debug("Loading exception: %s, %s.", Exception, e)
            tooltip(_("Could not open input file %s" % self.filename_import), period=1500)

        self.data.go_first()
        self.update_status()
        tooltip(_("All: %d (Dupe: %d)" % (self.data.len_all(), self.data.len_dupe())), period=1500)

    # todo: else statements!
    # cleanup: move to vocabulary class?
    def save(self):
        """ Saves self.added and self.rest to the resp. files """
        if os.path.exists(self.filename_added):
            with open(self.filename_added, 'wb') as file_:
                for item in self.data.get_added():
                    file_.write(item.line + "\n")
        if os.path.exists(self.filename_rest):
            with open(self.filename_rest, 'wb') as file_:
                for item in self.data.get_rest():
                    file_.write(item.line + "\n")
        if os.path.exists(self.filename_black):
            with open(self.filename_black, 'wb') as file_:
                for item in self.data.get_blacklisted():
                    file_.write(item.line + "\n")

    def show(self):
        """ Opens input file in an external editor. """
        if self.filename_import.strip():
            os.system(self.default_editor.format(filename=self.filename_import))
        else:
            tooltip(_("No input File!"), period=1500)

    # ========================= [ Reacting to user interaction ] =========================

    def go_anything(self):
        self.data.get_current().is_blacklisted = self.checkboxes["cbcQ_blacklist_current"].isChecked()
        self.checkboxes["cbcQ_blacklist_current"].setChecked(False)
        self.insert()

    def on_button_insert_clicked(self):
        """ Inserts the current entry from the queue into the Anki editor window"""
        self.go_anything()

    def on_button_last_clicked(self):
        """ Inserts last entry. """
        self.data.go_last()
        self.go_anything()

    def on_button_next_clicked(self):
        """ Inserts next entry. """
        self.data.go_next()
        self.go_anything()

    def on_button_previous_clicked(self):
        """ Inserts previous entry. """
        self.data.go_previous()
        self.go_anything()

    def on_button_first_clicked(self):
        """ Inserts first entry. """
        self.data.go_first()
        self.go_anything()

    def on_button_reverse_clicked(self):
        """ Reverses the ordering of the queue. """
        self.data.reverse()
        self.update_status()

    def on_choose_import_file(self):
        """ Opens a dialogue to let the user change the input file.
        :return: True if a file was chosen, False otherwise.
        """
        filters = "csv Files (*.csv);;tsv Files (*.tsv);;All Files (*)"
        import_file = QFileDialog.getSaveFileName(QFileDialog(), "Pick a file to import.",
                                                  self.default_dir, filters, options=QFileDialog.DontConfirmOverwrite)
        if import_file:
            self.filename_import = import_file
            self.update_filenames()
        return bool(import_file)

    def on_button_save_clicked(self):
        """ What happens if save button is pushed: Show tooltip and save."""
        self.save()
        tooltip(_("Saved!"), period=1500)

    def on_button_show_hide_clicked(self):
        self.hiding = not self.hiding
        self.update_visibility()

    def on_checkbox_changed(self):
        """ One of the checkboxes was clicked. Update settings etc. """
        # so that the settings have an effect on the queue implemented in self.data:
        self.data.dupes_in_queue = not self.checkboxes["cbcQ_skip_dupe"].isChecked()
        self.data.added_in_queue = not self.checkboxes["cbcQ_skip_added"].isChecked()
        self.data.blacklisted_in_queue = not self.checkboxes["cbcQ_skip_black"].isChecked()
        self.data.rest_in_queue = not self.checkboxes["cbcQ_skip_rest"].isChecked()
        # save checkbox states to config:
        for cb_name in self.checkboxes:
            self.config.set("ui_states", "{}_isChecked()".format(cb_name), str(self.checkboxes[cb_name].isChecked()))
        self.config.write_config()
        # update the ui
        self.update_status()
        self.update_enabled_disabled()

    # ========================= [ Anki Hooks ] =========================

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
        # save user input
        # this seems to be neccessary
        note.flush()
        # We have to check if the we really are adding an element
        # of the queue. Problem is that we want to allow some tolerance
        if self.data.is_expression_in_queue(note['Expression']):
            self.last_added = True
            self.data.get_current().is_added = True
            self.data.get_current().is_blacklisted = self.checkboxes["cbcQ_blacklist_current"].isChecked()
            self.checkboxes["cbcQ_blacklist_current"].setChecked(False)
            if self.checkboxes["cbcQ_auto_insert"].isChecked():
                # todo:
                print "auto insert"
                self.data.go_next()
                self.insert()
        else:
            self.last_added = False
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
            self.filename_import = glob.glob(os.path.expanduser("~/Desktop/*.csv"))[-1]
        except IndexError:
            self.filename_import = None
        self.filename_rest = os.path.expanduser('~/Desktop/rest.csv')

        self.setup_my_menu(editor)

    # ========================= [ Setup the GUI ] =========================

    def setup_my_menu(self, editor):
        """ Sets up the editor menu.
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
        self.button_box.setAlignment(aqt.qt.Qt.AlignCenter)
        self.status_box = QHBoxLayout()
        self.status_box.setAlignment(aqt.qt.Qt.AlignCenter)
        self.settings_box = QHBoxLayout()
        self.settings_box.setAlignment(aqt.qt.Qt.AlignCenter)

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
        self.add_toolbar_button("cbc_NewInputFile", [self.on_choose_import_file, self.update_enabled_disabled],
                                text=u"File", tip="Choose new input file.", size="30x80", )
        self.add_toolbar_button("cbc_Load", [self.load, self.update_enabled_disabled],
                                text=u"Load ⟲", tip="Load file", size="30x80", )
        self.add_toolbar_button("cbcQ_Show", [self.show, self.update_enabled_disabled],
                                text=u"Show", tip="Show file", size="30x60", )
        self.add_toolbar_button("cbcQ_Reverse", [self.on_button_reverse_clicked, self.update_enabled_disabled],
                                text=u"Reverse ⇄", tip="Reverse Order", size="30x90", )
        self.add_toolbar_button("cbcQ_Save", [self.on_button_save_clicked, self.update_enabled_disabled],
                                text=u"Save", tip="Saves all added resp. all remaining notes to two files.",
                                size="30x60")

        self.button_box.addItem(QSpacerItem(15, 1, QSizePolicy.Minimum, QSizePolicy.Preferred))
        self.add_toolbar_button("cbcQ_First", [self.on_button_first_clicked, self.update_enabled_disabled],
                                text=u"<<", tip="Fill in first entry", size="30x30", )
        self.add_toolbar_button("cbcQ_Previous", [self.on_button_previous_clicked, self.update_enabled_disabled],
                                text=u"<", tip="Fill in previous entry", size="30x30", )
        self.add_toolbar_button("cbcQ_Fill", [self.insert, self.update_enabled_disabled],
                                text=u"X↥", tip="Fill in form (Ctrl+F)", size="30x30",
                                key="Ctrl+F")
        self.add_toolbar_button("cbcQ_Next", [self.on_button_next_clicked, self.update_enabled_disabled],
                                text=u">", tip="Fill in next entry (Ctrl+G)", size="30x30",
                                key="Ctrl+G")
        self.add_toolbar_button("cbcQ_Last", [self.on_button_last_clicked, self.update_enabled_disabled],
                                text=u">>", tip="Fill in last entry", size="30x30", )

        self.button_box.addItem(QSpacerItem(15, 1, QSizePolicy.Minimum, QSizePolicy.Preferred))
        self.add_toolbar_button("cbc_show_hide", [self.on_button_show_hide_clicked], size="30x80")
        # text/tooltip will be updated below.

        self.add_settings_checkbox("cbcQ_skip_dupe", [self.on_checkbox_changed], "Skip Dupe",
                                   tip="Skip notes that are classified as duplicate by Anki.")
        self.add_settings_checkbox("cbcQ_skip_added", [self.on_checkbox_changed], "Skip Added",
                                   tip="Skip notes that were already added in this session of the cbcImport plugin.")
        self.add_settings_checkbox("cbcQ_skip_black", [self.on_checkbox_changed], "Skip Black",
                                   tip="Skip notes that were blacklisted.")
        self.add_settings_checkbox("cbcQ_skip_rest", [self.on_checkbox_changed], "Skip Rest",
                                   tip="Skip all notes that are neither added, blacklisted or classified as duplicate.")
        self.add_settings_checkbox("cbcQ_auto_insert", [self.on_checkbox_changed], "Auto Insert",
                                   tip="Automatically insert next expression, after note was added.")
        self.add_settings_checkbox("cbcQ_blacklist_current", [self.on_checkbox_changed], "Blacklist Current",
                                   tip="Blacklist current expression")

        self.status = QLabel()
        self.update_status()
        self.status_box.addWidget(self.status)

        self.update_enabled_disabled()
        self.update_visibility()
        self.on_checkbox_changed()

    # todo: docstring
    def update_visibility(self):
        text = u"Hide"
        tip = "Hide options and statistics."
        if not self.hiding:
            text = u"Advanced"
            tip = "Show options and statistics."
        self.buttons["cbc_show_hide"].setText(text)
        self.buttons["cbc_show_hide"].setToolTip(tip)

        for widget in layout_widgets(self.settings_box) + layout_widgets(self.status_box):
            widget.setVisible(self.hiding)

    def add_settings_checkbox(self, name, funcs, text="", tip=""):
        """ Shortcut to add a new checkbox to self.settings_box.
        :param name: We set self.settings_box[name] = checkbox
        :param funcs: List of functions the checkbox should be connected to when clicked
        :param text: Label of the checkbox
        :param tip: Tooltip
        :return: checkbox
        """
        checkbox = QCheckBox()
        checkbox.setText(text)
        checkbox.adjustSize()
        self.settings_box.addWidget(checkbox)
        self.checkboxes[name] = checkbox
        for func in funcs:
            checkbox.connect(checkbox, SIGNAL("clicked(bool)"), func)
        # try to set default value/saved value from config file (if set)
        try:
            checkbox.setChecked(self.config.getboolean("ui_states", "{}_isChecked()".format(name)))
        except (NoOptionError, NoSectionError):
            logger.warning("Missing a checkbox config option.".format())
            checkbox.setChecked(False)
        if tip:
            checkbox.setToolTip(shortcut(tip))
        return checkbox

    def add_toolbar_button(self, name, funcs, key=None, tip=None, size="30x50", text=u"", check=False):
        """ Shortcut to add a new button to self.button_box.
        :param name: We set self.buttons[name] = button
        :param funcs: List of functions the button should be connected to when clicked
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

    # ========================= [ Update the GUI ] =========================

    def update_filenames(self):
        if not os.path.exists(self.filename_import):
            logger.warning("Import file {} does not exist.".format(os.path.abspath(self.filename_import)))
            self.filename_added = ""
            self.filename_rest = ""
            self.filename_black = ""
            self.update_status()
            return
        dirname = os.path.dirname(self.filename_import)
        basename, ext = os.path.splitext(os.path.basename(self.filename_import))
        self.filename_added = os.path.join(dirname, "{}_added{}".format(basename, ext))
        self.filename_rest = os.path.join(dirname, "{}_rest{}".format(basename, ext))
        self.filename_black = os.path.join(dirname, "{}_black{}".format(basename, ext))
        self.update_status()

    def update_enabled_disabled(self):
        """ Enables/Disables buttons/checkboxes based on the state of the addon """
        # note the difference between VocabularyCollection.queue_empty()
        # and VocabularyCollection.empty()
        if not self.data.is_queue_empty():
            for buttonName in self.buttons:
                if buttonName.startswith('cbcQ_'):
                    self.buttons[buttonName].setEnabled(True)
        if not self.data.is_empty():
            for checkboxName in self.checkboxes:
                if checkboxName.startswith('cbcQ_'):
                    self.checkboxes[checkboxName].setEnabled(True)
        self.buttons["cbcQ_Next"].setEnabled(self.data.is_go_next_possible())
        self.buttons["cbcQ_Last"].setEnabled(self.data.is_go_next_possible())
        self.buttons["cbcQ_Previous"].setEnabled(self.data.is_go_previous_possible())
        self.buttons["cbcQ_First"].setEnabled(self.data.is_go_previous_possible())
        # note the difference between VocabularyCollection.queue_empty()
        # and VocabularyCollection.empty()
        if self.data.is_queue_empty():
            for buttonName in self.buttons:
                if buttonName.startswith('cbcQ_'):
                    self.buttons[buttonName].setEnabled(False)
        if self.data.is_empty():
            for checkboxName in self.checkboxes:
                if checkboxName.startswith('cbcQ_'):
                    self.checkboxes[checkboxName].setEnabled(False)

    def update_status(self):
        """ Updates the status label to display number of remaining entries etc. """

        # future: make single labels so that we can make them clickable etc.

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

        def format_key_value(key, value, symbol=""):
            return "<b>{}:</b> {}{}".format(key, red(value), symbol)

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
        texts = [format_key_value("In", shorten(self.filename_import, length=20)),
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

        tooltips = ["In: Name of the input file.",
                    "Cur: Index of the current item in the queue/Total number of items in the queue",
                    "Idx: Index of the current item/Total number of items",
                    "Add: Number of added notes.",
                    "Dup: Number of duplicate notes.",
                    "Black: Number of blacklisted notes.",
                    "LA: Was the last note counted as \"added\"?"]

        self.status.setText('&nbsp;&nbsp;'.join(texts))
        self.status.setToolTip('\n'.join(tooltips))
