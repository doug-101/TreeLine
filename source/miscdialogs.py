#!/usr/bin/env python3

#******************************************************************************
# miscdialogs.py, provides classes for various control dialogs
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import enum
import re
import sys
import operator
import collections
import datetime
import platform
import traceback
from PyQt5.QtCore import Qt, pyqtSignal, PYQT_VERSION_STR, qVersion
from PyQt5.QtGui import QFont, QKeySequence, QTextDocument, QTextOption
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                             QCheckBox, QComboBox, QDialog, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QRadioButton,
                             QScrollArea, QSpinBox, QTabWidget, QTextEdit,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)
import options
import printdialogs
import undo
import globalref
try:
    from __main__ import __version__
except ImportError:
    __version__ = ''


class RadioChoiceDialog(QDialog):
    """Dialog for choosing between a list of text items (radio buttons).

    Dialog title, group heading, button text and return text can be set.
    """
    def __init__(self, title, heading, choiceList, parent=None):
        """Create the radio choice dialog.

        Arguments:
            title -- the window title
            heading -- the groupbox text
            choiceList -- tuples of button text and return values
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(title)
        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)

        groupBox = QGroupBox(heading)
        topLayout.addWidget(groupBox)
        groupLayout = QVBoxLayout(groupBox)
        self.buttonGroup = QButtonGroup(self)
        for text, value in choiceList:
            if value != None:
                button = QRadioButton(text)
                button.returnValue = value
                groupLayout.addWidget(button)
                self.buttonGroup.addButton(button)
            else:  # add heading if no return value
                label = QLabel('<b>{0}:</b>'.format(text))
                groupLayout.addWidget(label)
        self.buttonGroup.buttons()[0].setChecked(True)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        groupBox.setFocus()

    def addLabelBox(self, heading, text):
        """Add a group box with text above the radio button group.

        Arguments:
            heading -- the groupbox text
            text - the label text
        """
        labelBox = QGroupBox(heading)
        self.layout().insertWidget(0, labelBox)
        labelLayout =  QVBoxLayout(labelBox)
        label = QLabel(text)
        labelLayout.addWidget(label)

    def selectedButton(self):
        """Return the value of the selected button.
        """
        return self.buttonGroup.checkedButton().returnValue


class FieldSelectDialog(QDialog):
    """Dialog for selecting a sequence from a list of field names.
    """
    def __init__(self, title, heading, fieldList, parent=None):
        """Create the field select dialog.

        Arguments:
            title -- the window title
            heading -- the groupbox text
            fieldList -- the list of field names to select
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(title)
        self.selectedFields = []
        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        groupBox = QGroupBox(heading)
        topLayout.addWidget(groupBox)
        groupLayout = QVBoxLayout(groupBox)

        self.listView = QTreeWidget()
        groupLayout.addWidget(self.listView)
        self.listView.setHeaderLabels(['#', _('Fields')])
        self.listView.setRootIsDecorated(False)
        self.listView.setSortingEnabled(False)
        self.listView.setSelectionMode(QAbstractItemView.MultiSelection)
        for field in fieldList:
            QTreeWidgetItem(self.listView, ['', field])
        self.listView.resizeColumnToContents(0)
        self.listView.resizeColumnToContents(1)
        self.listView.itemSelectionChanged.connect(self.updateSelectedFields)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        self.okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        self.okButton.setEnabled(False)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.listView.setFocus()

    def updateSelectedFields(self):
        """Update the TreeView and the list of selected fields.
        """
        itemList = [self.listView.topLevelItem(i) for i in
                    range(self.listView.topLevelItemCount())]
        for item in itemList:
            if item.isSelected():
                if item.text(1) not in self.selectedFields:
                    self.selectedFields.append(item.text(1))
            elif item.text(1) in self.selectedFields:
                self.selectedFields.remove(item.text(1))
        for item in itemList:
            if item.isSelected():
                item.setText(0, str(self.selectedFields.index(item.text(1))
                                    + 1))
            else:
                item.setText(0, '')
        self.okButton.setEnabled(len(self.selectedFields))


class FilePropertiesDialog(QDialog):
    """Dialog for setting file parameters like compression and encryption.
    """
    def __init__(self, localControl, parent=None):
        """Create the file properties dialog.

        Arguments:
            localControl -- a reference to the file's local control
            parent -- the parent window
        """
        super().__init__(parent)
        self.localControl = localControl
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('File Properties'))
        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)

        groupBox = QGroupBox(_('File Storage'))
        topLayout.addWidget(groupBox)
        groupLayout = QVBoxLayout(groupBox)
        self.compressCheck = QCheckBox(_('&Use file compression'))
        self.compressCheck.setChecked(localControl.compressed)
        groupLayout.addWidget(self.compressCheck)
        self.encryptCheck = QCheckBox(_('Use file &encryption'))
        self.encryptCheck.setChecked(localControl.encrypted)
        groupLayout.addWidget(self.encryptCheck)

        groupBox = QGroupBox(_('Spell Check'))
        topLayout.addWidget(groupBox)
        groupLayout = QHBoxLayout(groupBox)
        label = QLabel(_('Language code or\ndictionary (optional)'))
        groupLayout.addWidget(label)
        self.spellCheckEdit = QLineEdit()
        self.spellCheckEdit.setText(self.localControl.spellCheckLang)
        groupLayout.addWidget(self.spellCheckEdit)

        groupBox = QGroupBox(_('Math Fields'))
        topLayout.addWidget(groupBox)
        groupLayout = QVBoxLayout(groupBox)
        self.zeroBlanks = QCheckBox(_('&Treat blank fields as zeros'))
        self.zeroBlanks.setChecked(localControl.structure.mathZeroBlanks)
        groupLayout.addWidget(self.zeroBlanks)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def accept(self):
        """Store the results.
        """
        if (self.localControl.compressed != self.compressCheck.isChecked() or
            self.localControl.encrypted != self.encryptCheck.isChecked() or
            self.localControl.spellCheckLang != self.spellCheckEdit.text() or
            self.localControl.structure.mathZeroBlanks !=
            self.zeroBlanks.isChecked()):
            undo.ParamUndo(self.localControl.structure.undoList,
                           [(self.localControl, 'compressed'),
                            (self.localControl, 'encrypted'),
                            (self.localControl, 'spellCheckLang'),
                            (self.localControl.structure, 'mathZeroBlanks')])
            self.localControl.compressed = self.compressCheck.isChecked()
            self.localControl.encrypted = self.encryptCheck.isChecked()
            self.localControl.spellCheckLang = self.spellCheckEdit.text()
            self.localControl.structure.mathZeroBlanks = (self.zeroBlanks.
                                                          isChecked())
            super().accept()
        else:
            super().reject()


class PasswordDialog(QDialog):
    """Dialog for password entry and optional re-entry.
    """
    remember = True
    def __init__(self, retype=True, fileLabel='', parent=None):
        """Create the password dialog.

        Arguments:
            retype -- require a 2nd password entry if True
            fileLabel -- file name to show if given
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Encrypted File Password'))
        self.password = ''
        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        if fileLabel:
            prompt = _('Type Password for "{0}":').format(fileLabel)
        else:
            prompt = _('Type Password:')
        self.editors = [self.addEditor(prompt, topLayout)]
        self.editors[0].setFocus()
        if retype:
            self.editors.append(self.addEditor(_('Re-Type Password:'),
                                               topLayout))
            self.editors[0].returnPressed.connect(self.editors[1].setFocus)
        self.editors[-1].returnPressed.connect(self.accept)
        self.rememberCheck = QCheckBox(_('Remember password during this '
                                               'session'))
        self.rememberCheck.setChecked(PasswordDialog.remember)
        topLayout.addWidget(self.rememberCheck)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        okButton = QPushButton(_('&OK'))
        okButton.setAutoDefault(False)
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        cancelButton.setAutoDefault(False)
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def addEditor(self, labelText, layout):
        """Add a password editor to this dialog and return it.

        Arguments:
            labelText -- the text for the label
            layout -- the layout to append it
        """
        label = QLabel(labelText)
        layout.addWidget(label)
        editor = QLineEdit()
        editor.setEchoMode(QLineEdit.Password)
        layout.addWidget(editor)
        return editor

    def accept(self):
        """Check for valid password and store the result.
        """
        self.password = self.editors[0].text()
        PasswordDialog.remember = self.rememberCheck.isChecked()
        if not self.password:
            QMessageBox.warning(self, 'TreeLine',
                                  _('Zero-length passwords are not permitted'))
        elif len(self.editors) > 1 and self.editors[1].text() != self.password:
             QMessageBox.warning(self, 'TreeLine',
                                       _('Re-typed password did not match'))
        else:
            super().accept()
        for editor in self.editors:
            editor.clear()
        self.editors[0].setFocus()


class TemplateFileItem:
    """Helper class to store template paths and info.
    """
    nameExp = re.compile(r'(\d+)([a-zA-Z]+?)_(.+)')
    def __init__(self, pathObj):
        """Initialize the path.

        Arguments:
            pathObj -- the full path object
        """
        self.pathObj = pathObj
        self.number = sys.maxsize
        self.name = ''
        self.displayName = ''
        self.langCode = ''
        if pathObj:
            self.name = pathObj.stem
            match = TemplateFileItem.nameExp.match(self.name)
            if match:
                num, self.langCode, self.name = match.groups()
                self.number = int(num)
            self.displayName = self.name.replace('_', ' ')

    def sortKey(self):
        """Return a key for sorting the items by number then name.
        """
        return (self.number, self.displayName)

    def __eq__(self, other):
        """Comparison to detect equivalent items.

        Arguments:
            other -- the TemplateFileItem to compare
        """
        return (self.displayName == other.displayName and
                self.langCode == other.langCode)

    def __hash__(self):
        """Return a hash code for use in sets and dictionaries.
        """
        return hash((self.langCode, self.displayName))


class TemplateFileDialog(QDialog):
    """Dialog for listing available template files.
    """
    def __init__(self, title, heading, searchPaths, addDefault=True,
                 parent=None):
        """Create the template dialog.

        Arguments:
            title -- the window title
            heading -- the groupbox text
            searchPaths -- list of path objects with available templates
            addDefault -- if True, add a default (no path) entry
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(title)
        self.templateItems = []
        if addDefault:
            item = TemplateFileItem(None)
            item.number = -1
            item.displayName = _('Default - Single Line Text')
            self.templateItems.append(item)

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        groupBox = QGroupBox(heading)
        topLayout.addWidget(groupBox)
        boxLayout = QVBoxLayout(groupBox)
        self.listBox = QListWidget()
        boxLayout.addWidget(self.listBox)
        self.listBox.itemDoubleClicked.connect(self.accept)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        self.okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

        self.readTemplates(searchPaths)
        self.loadListBox()

    def readTemplates(self, searchPaths):
        """Read template file paths into the templateItems list.

        Arguments:
            searchPaths -- list of path objects with available templates
        """
        templateItems = set()
        for path in searchPaths:
            for templatePath in path.glob('*.trln'):
                templateItem = TemplateFileItem(templatePath)
                if templateItem not in templateItems:
                    templateItems.add(templateItem)
        availLang = set([item.langCode for item in templateItems])
        if len(availLang) > 1:
            lang = 'en'
            if globalref.lang[:2] in availLang:
                lang = globalref.lang[:2]
            templateItems = [item for item in templateItems if
                             item.langCode == lang or not item.langCode]
        self.templateItems.extend(list(templateItems))
        self.templateItems.sort(key = operator.methodcaller('sortKey'))

    def loadListBox(self):
        """Load the list box with items from the templateItems list.
        """
        self.listBox.clear()
        self.listBox.addItems([item.displayName for item in
                               self.templateItems])
        self.listBox.setCurrentRow(0)
        self.okButton.setEnabled(self.listBox.count() > 0)

    def selectedPath(self):
        """Return the path object from the selected item.
        """
        item = self.templateItems[self.listBox.currentRow()]
        return item.pathObj

    def selectedName(self):
        """Return the displayed name with underscores from the selected item.
        """
        item = self.templateItems[self.listBox.currentRow()]
        return item.name


class ExceptionDialog(QDialog):
    """Dialog for showing debug info from an unhandled exception.
    """
    def __init__(self, excType, value, tb, parent=None):
        """Initialize the exception dialog.

        Arguments:
            excType -- execption class
            value -- execption error text
            tb -- the traceback object
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle(_('TreeLine - Serious Error'))

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        label = QLabel(_('A serious error has occurred.  TreeLine could be '
                         'in an unstable state.\n'
                         'Recommend saving any file changes under another '
                         'filename and restart TreeLine.\n\n'
                         'The debugging info shown below can be copied '
                         'and emailed to doug101@bellz.org along with\n'
                         'an explanation of the circumstances.\n'))
        topLayout.addWidget(label)
        textBox = QTextEdit()
        textBox.setReadOnly(True)
        pyVersion = '.'.join([repr(num) for num in sys.version_info[:3]])
        textLines = ['When:  {0}\n'.format(datetime.datetime.now().
                                           isoformat(' ')),
                     'TreeLine Version:  {0}\n'.format(__version__),
                     'Python Version:  {0}\n'.format(pyVersion),
                     'Qt Version:  {0}\n'.format(qVersion()),
                     'PyQt Version:  {0}\n'.format(PYQT_VERSION_STR),
                     'OS:  {0}\n'.format(platform.platform()), '\n']
        textLines.extend(traceback.format_exception(excType, value, tb))
        textBox.setPlainText(''.join(textLines))
        topLayout.addWidget(textBox)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        closeButton = QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)


FindScope = enum.IntEnum('FindScope', 'fullData titlesOnly')
FindType = enum.IntEnum('FindType', 'keyWords fullWords fullPhrase regExp')

class FindFilterDialog(QDialog):
    """Dialog for searching for text within tree titles and data.
    """
    dialogShown = pyqtSignal(bool)
    def __init__(self, isFilterDialog=False, parent=None):
        """Initialize the find dialog.

        Arguments:
            isFilterDialog -- True for filter dialog, False for find dialog
            parent -- the parent window
        """
        super().__init__(parent)
        self.isFilterDialog = isFilterDialog
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)

        textBox = QGroupBox(_('&Search Text'))
        topLayout.addWidget(textBox)
        textLayout = QVBoxLayout(textBox)
        self.textEntry = QLineEdit()
        textLayout.addWidget(self.textEntry)
        self.textEntry.textEdited.connect(self.updateAvail)

        horizLayout = QHBoxLayout()
        topLayout.addLayout(horizLayout)

        whatBox = QGroupBox(_('What to Search'))
        horizLayout.addWidget(whatBox)
        whatLayout = QVBoxLayout(whatBox)
        self.whatButtons = QButtonGroup(self)
        button = QRadioButton(_('Full &data'))
        self.whatButtons.addButton(button, FindScope.fullData)
        whatLayout.addWidget(button)
        button = QRadioButton(_('&Titles only'))
        self.whatButtons.addButton(button, FindScope.titlesOnly)
        whatLayout.addWidget(button)
        self.whatButtons.button(FindScope.fullData).setChecked(True)

        howBox = QGroupBox(_('How to Search'))
        horizLayout.addWidget(howBox)
        howLayout = QVBoxLayout(howBox)
        self.howButtons = QButtonGroup(self)
        button = QRadioButton(_('&Key words'))
        self.howButtons.addButton(button, FindType.keyWords)
        howLayout.addWidget(button)
        button = QRadioButton(_('Key full &words'))
        self.howButtons.addButton(button, FindType.fullWords)
        howLayout.addWidget(button)
        button = QRadioButton(_('F&ull phrase'))
        self.howButtons.addButton(button, FindType.fullPhrase)
        howLayout.addWidget(button)
        button = QRadioButton(_('&Regular expression'))
        self.howButtons.addButton(button, FindType.regExp)
        howLayout.addWidget(button)
        self.howButtons.button(FindType.keyWords).setChecked(True)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        if not self.isFilterDialog:
            self.setWindowTitle(_('Find'))
            self.previousButton = QPushButton(_('Find &Previous'))
            ctrlLayout.addWidget(self.previousButton)
            self.previousButton.clicked.connect(self.findPrevious)
            self.nextButton = QPushButton(_('Find &Next'))
            self.nextButton.setDefault(True)
            ctrlLayout.addWidget(self.nextButton)
            self.nextButton.clicked.connect(self.findNext)
            self.resultLabel = QLabel()
            topLayout.addWidget(self.resultLabel)
        else:
            self.setWindowTitle(_('Filter'))
            self.filterButton = QPushButton(_('&Filter'))
            ctrlLayout.addWidget(self.filterButton)
            self.filterButton.clicked.connect(self.startFilter)
            self.endFilterButton = QPushButton(_('&End Filter'))
            ctrlLayout.addWidget(self.endFilterButton)
            self.endFilterButton.clicked.connect(self.endFilter)
        closeButton = QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)
        self.updateAvail('')

    def selectAllText(self):
        """Select all line edit text to prepare for a new entry.
        """
        self.textEntry.selectAll()
        self.textEntry.setFocus()

    def updateAvail(self, text='', fileChange=False):
        """Make find buttons available if search text exists.

        Arguments:
            text -- placeholder for signal text (not used)
            fileChange -- True if window changed while dialog open
        """
        hasEntry = len(self.textEntry.text().strip()) > 0
        if not self.isFilterDialog:
            self.previousButton.setEnabled(hasEntry)
            self.nextButton.setEnabled(hasEntry)
            self.resultLabel.setText('')
        else:
            window = globalref.mainControl.activeControl.activeWindow
            if fileChange and window.treeFilterView:
                filterView = window.treeFilterView
                self.textEntry.setText(filterView.filterStr)
                self.whatButtons.button(filterView.filterWhat).setChecked(True)
                self.howButtons.button(filterView.filterHow).setChecked(True)
            self.filterButton.setEnabled(hasEntry)
            self.endFilterButton.setEnabled(window.treeFilterView != None)

    def find(self, forward=True):
        """Find another match in the indicated direction.

        Arguments:
            forward -- next if True, previous if False
        """
        self.resultLabel.setText('')
        text = self.textEntry.text()
        titlesOnly = self.whatButtons.checkedId() == (FindScope.titlesOnly)
        control = globalref.mainControl.activeControl
        if self.howButtons.checkedId() == FindType.regExp:
            try:
                regExp = re.compile(text)
            except re.error:
                QMessageBox.warning(self, 'TreeLine',
                                    _('Error - invalid regular expression'))
                return
            result = control.findNodesByRegExp([regExp], titlesOnly, forward)
        elif self.howButtons.checkedId() == FindType.fullWords:
            regExpList = []
            for word in text.lower().split():
                regExpList.append(re.compile(r'(?i)\b{}\b'.
                                             format(re.escape(word))))
            result = control.findNodesByRegExp(regExpList, titlesOnly, forward)
        elif self.howButtons.checkedId() == FindType.keyWords:
            wordList = text.lower().split()
            result = control.findNodesByWords(wordList, titlesOnly, forward)
        else:         # full phrase
            wordList = [text.lower().strip()]
            result = control.findNodesByWords(wordList, titlesOnly, forward)
        if not result:
            self.resultLabel.setText(_('Search string "{0}" not found').
                                     format(text))

    def findPrevious(self):
        """Find the previous match.
        """
        self.find(False)

    def findNext(self):
        """Find the next match.
        """
        self.find(True)

    def startFilter(self):
        """Start filtering nodes.
        """
        if self.howButtons.checkedId() == FindType.regExp:
            try:
                re.compile(self.textEntry.text())
            except re.error:
                QMessageBox.warning(self, 'TreeLine',
                                       _('Error - invalid regular expression'))
                return
        filterView = (globalref.mainControl.activeControl.activeWindow.
                      filterView())
        filterView.filterWhat = self.whatButtons.checkedId()
        filterView.filterHow = self.howButtons.checkedId()
        filterView.filterStr = self.textEntry.text()
        filterView.updateContents()
        self.updateAvail()

    def endFilter(self):
        """Stop filtering nodes.
        """
        globalref.mainControl.activeControl.activeWindow.removeFilterView()
        self.updateAvail()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


FindReplaceType = enum.IntEnum('FindReplaceType', 'anyMatch fullWord regExp')

class FindReplaceDialog(QDialog):
    """Dialog for finding and replacing text in the node data.
    """
    dialogShown = pyqtSignal(bool)
    def __init__(self, parent=None):
        """Initialize the find and replace dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle(_('Find and Replace'))

        self.matchedSpot = None
        topLayout = QGridLayout(self)
        self.setLayout(topLayout)

        textBox = QGroupBox(_('&Search Text'))
        topLayout.addWidget(textBox, 0, 0)
        textLayout = QVBoxLayout(textBox)
        self.textEntry = QLineEdit()
        textLayout.addWidget(self.textEntry)
        self.textEntry.textEdited.connect(self.clearMatch)

        replaceBox = QGroupBox(_('Replacement &Text'))
        topLayout.addWidget(replaceBox, 0, 1)
        replaceLayout = QVBoxLayout(replaceBox)
        self.replaceEntry = QLineEdit()
        replaceLayout.addWidget(self.replaceEntry)

        howBox = QGroupBox(_('How to Search'))
        topLayout.addWidget(howBox, 1, 0, 2, 1)
        howLayout = QVBoxLayout(howBox)
        self.howButtons = QButtonGroup(self)
        button = QRadioButton(_('Any &match'))
        self.howButtons.addButton(button, FindReplaceType.anyMatch)
        howLayout.addWidget(button)
        button = QRadioButton(_('Full &words'))
        self.howButtons.addButton(button, FindReplaceType.fullWord)
        howLayout.addWidget(button)
        button = QRadioButton(_('Re&gular expression'))
        self.howButtons.addButton(button, FindReplaceType.regExp)
        howLayout.addWidget(button)
        self.howButtons.button(FindReplaceType.anyMatch).setChecked(True)
        self.howButtons.buttonClicked.connect(self.clearMatch)

        typeBox = QGroupBox(_('&Node Type'))
        topLayout.addWidget(typeBox, 1, 1)
        typeLayout = QVBoxLayout(typeBox)
        self.typeCombo = QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged.connect(self.loadFieldNames)

        fieldBox = QGroupBox(_('N&ode Fields'))
        topLayout.addWidget(fieldBox, 2, 1)
        fieldLayout = QVBoxLayout(fieldBox)
        self.fieldCombo = QComboBox()
        fieldLayout.addWidget(self.fieldCombo)
        self.fieldCombo.currentIndexChanged.connect(self.clearMatch)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout, 3, 0, 1, 2)
        self.previousButton = QPushButton(_('Find &Previous'))
        ctrlLayout.addWidget(self.previousButton)
        self.previousButton.clicked.connect(self.findPrevious)
        self.nextButton = QPushButton(_('&Find Next'))
        self.nextButton.setDefault(True)
        ctrlLayout.addWidget(self.nextButton)
        self.nextButton.clicked.connect(self.findNext)
        self.replaceButton = QPushButton(_('&Replace'))
        ctrlLayout.addWidget(self.replaceButton)
        self.replaceButton.clicked.connect(self.replace)
        self.replaceAllButton = QPushButton(_('Replace &All'))
        ctrlLayout.addWidget(self.replaceAllButton)
        self.replaceAllButton.clicked.connect(self.replaceAll)
        closeButton = QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)

        self.resultLabel = QLabel()
        topLayout.addWidget(self.resultLabel, 4, 0, 1, 2)
        self.loadTypeNames()
        self.updateAvail()

    def updateAvail(self):
        """Set find & replace buttons available if search text & matches exist.
        """
        hasEntry = len(self.textEntry.text().strip()) > 0
        self.previousButton.setEnabled(hasEntry)
        self.nextButton.setEnabled(hasEntry)
        match = bool(self.matchedSpot and self.matchedSpot is
                     globalref.mainControl.activeControl.
                     currentSelectionModel().currentSpot())
        self.replaceButton.setEnabled(match)
        self.replaceAllButton.setEnabled(match)
        self.resultLabel.setText('')

    def clearMatch(self):
        """Remove reference to matched node if search criteria changes.
        """
        self.matchedSpot = None
        globalref.mainControl.activeControl.findReplaceSpotRef = (None, 0)
        self.updateAvail()

    def loadTypeNames(self):
        """Load format type names into combo box.
        """
        origTypeName = self.typeCombo.currentText()
        nodeFormats = globalref.mainControl.activeControl.structure.treeFormats
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        typeNames = nodeFormats.typeNames()
        self.typeCombo.addItems([_('[All Types]')] + typeNames)
        origPos = self.typeCombo.findText(origTypeName)
        if origPos >= 0:
            self.typeCombo.setCurrentIndex(origPos)
        self.typeCombo.blockSignals(False)
        self.loadFieldNames()

    def loadFieldNames(self):
        """Load field names into combo box.
        """
        origFieldName = self.fieldCombo.currentText()
        nodeFormats = globalref.mainControl.activeControl.structure.treeFormats
        typeName = self.typeCombo.currentText()
        fieldNames = []
        if typeName.startswith('['):
            for typeName in nodeFormats.typeNames():
                for fieldName in nodeFormats[typeName].fieldNames():
                    if fieldName not in fieldNames:
                        fieldNames.append(fieldName)
        else:
            fieldNames.extend(nodeFormats[typeName].fieldNames())
        self.fieldCombo.clear()
        self.fieldCombo.addItems([_('[All Fields]')] + fieldNames)
        origPos = self.fieldCombo.findText(origFieldName)
        if origPos >= 0:
            self.fieldCombo.setCurrentIndex(origPos)
        self.matchedSpot = None
        self.updateAvail()

    def findParameters(self):
        """Create search parameters based on the dialog settings.

        Return a tuple of searchText, regExpObj, typeName, and fieldName.
        """
        text = self.textEntry.text()
        searchText = ''
        regExpObj = None
        if self.howButtons.checkedId() == FindReplaceType.anyMatch:
            searchText = text.lower().strip()
        elif self.howButtons.checkedId() == FindReplaceType.fullWord:
            regExpObj = re.compile(r'(?i)\b{}\b'.format(re.escape(text)))
        else:
            regExpObj = re.compile(text)
        typeName = self.typeCombo.currentText()
        if typeName.startswith('['):
            typeName = ''
        fieldName = self.fieldCombo.currentText()
        if fieldName.startswith('['):
            fieldName = ''
        return (searchText, regExpObj, typeName, fieldName)

    def find(self, forward=True):
        """Find another match in the indicated direction.

        Arguments:
            forward -- next if True, previous if False
        """
        self.matchedSpot = None
        try:
            searchText, regExpObj, typeName, fieldName = self.findParameters()
        except re.error:
            QMessageBox.warning(self, 'TreeLine',
                                      _('Error - invalid regular expression'))
            self.updateAvail()
            return
        control = globalref.mainControl.activeControl
        if control.findNodesForReplace(searchText, regExpObj, typeName,
                                       fieldName, forward):
            self.matchedSpot = control.currentSelectionModel().currentSpot()
            self.updateAvail()
        else:
            self.updateAvail()
            self.resultLabel.setText(_('Search text "{0}" not found').
                                     format(self.textEntry.text()))

    def findPrevious(self):
        """Find the previous match.
        """
        self.find(False)

    def findNext(self):
        """Find the next match.
        """
        self.find(True)

    def replace(self):
        """Replace the currently found text.
        """
        searchText, regExpObj, typeName, fieldName = self.findParameters()
        replaceText = self.replaceEntry.text()
        control = globalref.mainControl.activeControl
        if control.replaceInCurrentNode(searchText, regExpObj, typeName,
                                        fieldName, replaceText):
            self.find()
        else:
            QMessageBox.warning(self, 'TreeLine',
                                      _('Error - replacement failed'))
            self.matchedSpot = None
            self.updateAvail()

    def replaceAll(self):
        """Replace all text matches.
        """
        searchText, regExpObj, typeName, fieldName = self.findParameters()
        replaceText = self.replaceEntry.text()
        control = globalref.mainControl.activeControl
        qty = control.replaceAll(searchText, regExpObj, typeName, fieldName,
                                 replaceText)
        self.matchedSpot = None
        self.updateAvail()
        self.resultLabel.setText(_('Replaced {0} matches').format(qty))

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


SortWhat = enum.IntEnum('SortWhat',
                        'fullTree selectBranch selectChildren selectSiblings')
SortMethod = enum.IntEnum('SortMethod', 'fieldSort titleSort')
SortDirection = enum.IntEnum('SortDirection', 'forward reverse')

class SortDialog(QDialog):
    """Dialog for defining sort operations.
    """
    dialogShown = pyqtSignal(bool)
    def __init__(self, parent=None):
        """Initialize the sort dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle(_('Sort Nodes'))

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        horizLayout = QHBoxLayout()
        topLayout.addLayout(horizLayout)
        whatBox = QGroupBox(_('What to Sort'))
        horizLayout.addWidget(whatBox)
        whatLayout = QVBoxLayout(whatBox)
        self.whatButtons = QButtonGroup(self)
        button = QRadioButton(_('&Entire tree'))
        self.whatButtons.addButton(button, SortWhat.fullTree)
        whatLayout.addWidget(button)
        button = QRadioButton(_('Selected &branches'))
        self.whatButtons.addButton(button, SortWhat.selectBranch)
        whatLayout.addWidget(button)
        button = QRadioButton(_('Selection\'s childre&n'))
        self.whatButtons.addButton(button, SortWhat.selectChildren)
        whatLayout.addWidget(button)
        button = QRadioButton(_('Selection\'s &siblings'))
        self.whatButtons.addButton(button, SortWhat.selectSiblings)
        whatLayout.addWidget(button)
        self.whatButtons.button(SortWhat.fullTree).setChecked(True)

        vertLayout =  QVBoxLayout()
        horizLayout.addLayout(vertLayout)
        methodBox = QGroupBox(_('Sort Method'))
        vertLayout.addWidget(methodBox)
        methodLayout = QVBoxLayout(methodBox)
        self.methodButtons = QButtonGroup(self)
        button = QRadioButton(_('&Predefined Key Fields'))
        self.methodButtons.addButton(button, SortMethod.fieldSort)
        methodLayout.addWidget(button)
        button = QRadioButton(_('Node &Titles'))
        self.methodButtons.addButton(button, SortMethod.titleSort)
        methodLayout.addWidget(button)
        self.methodButtons.button(SortMethod.fieldSort).setChecked(True)

        directionBox = QGroupBox(_('Sort Direction'))
        vertLayout.addWidget(directionBox)
        directionLayout =  QVBoxLayout(directionBox)
        self.directionButtons = QButtonGroup(self)
        button = QRadioButton(_('&Forward'))
        self.directionButtons.addButton(button, SortDirection.forward)
        directionLayout.addWidget(button)
        button = QRadioButton(_('&Reverse'))
        self.directionButtons.addButton(button, SortDirection.reverse)
        directionLayout.addWidget(button)
        self.directionButtons.button(SortDirection.forward).setChecked(True)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.sortAndClose)
        applyButton = QPushButton(_('&Apply'))
        ctrlLayout.addWidget(applyButton)
        applyButton.clicked.connect(self.sortNodes)
        closeButton = QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)
        self.updateCommandsAvail()

    def updateCommandsAvail(self):
        """Set what to sort options available based on tree selections.
        """
        selModel = globalref.mainControl.activeControl.currentSelectionModel()
        hasChild = False
        hasSibling = False
        for spot in selModel.selectedSpots():
            if spot.nodeRef.childList:
                hasChild = True
            if spot.parentSpot and len(spot.parentSpot.nodeRef.childList) > 1:
                hasSibling = True
        self.whatButtons.button(SortWhat.selectBranch).setEnabled(hasChild)
        self.whatButtons.button(SortWhat.selectChildren).setEnabled(hasChild)
        self.whatButtons.button(SortWhat.selectSiblings).setEnabled(hasSibling)
        if not self.whatButtons.checkedButton().isEnabled():
            self.whatButtons.button(SortWhat.fullTree).setChecked(True)

    def sortNodes(self):
        """Perform the sorting operation.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        control = globalref.mainControl.activeControl
        selSpots = control.currentSelectionModel().selectedSpots()
        if self.whatButtons.checkedId() == SortWhat.fullTree:
            selSpots = [control.structure.spotByNumber(0)]
        elif self.whatButtons.checkedId() == SortWhat.selectSiblings:
            selSpots = [spot.parentSpot for spot in selSpots]
        if self.whatButtons.checkedId() in (SortWhat.fullTree,
                                            SortWhat.selectBranch):
            rootSpots = selSpots[:]
            selSpots = []
            for root in rootSpots:
                for spot in root.spotDescendantGen():
                    if spot.nodeRef.childList:
                        selSpots.append(spot)
        undo.ChildListUndo(control.structure.undoList,
                           [spot.nodeRef for spot in selSpots])
        forward = self.directionButtons.checkedId() == SortDirection.forward
        if self.methodButtons.checkedId() == SortMethod.fieldSort:
            for spot in selSpots:
                spot.nodeRef.sortChildrenByField(False, forward)
            # reset temporary sort field storage
            for nodeFormat in control.structure.treeFormats.values():
                nodeFormat.sortFields = []
        else:
            for spot in selSpots:
                spot.nodeRef.sortChildrenByTitle(False, forward)
        control.updateAll()
        QApplication.restoreOverrideCursor()

    def sortAndClose(self):
        """Perform the sorting operation and close the dialog.
        """
        self.sortNodes()
        self.close()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


NumberingScope = enum.IntEnum('NumberingScope',
                              'fullTree selectBranch selectChildren')
NumberingNoField = enum.IntEnum('NumberingNoField',
                            'ignoreNoField restartAfterNoField reserveNoField')

class NumberingDialog(QDialog):
    """Dialog for updating node nuumbering fields.
    """
    dialogShown = pyqtSignal(bool)
    def __init__(self, parent=None):
        """Initialize the numbering dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle(_('Update Node Numbering'))

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        whatBox = QGroupBox(_('What to Update'))
        topLayout.addWidget(whatBox)
        whatLayout = QVBoxLayout(whatBox)
        self.whatButtons = QButtonGroup(self)
        button = QRadioButton(_('&Entire tree'))
        self.whatButtons.addButton(button, NumberingScope.fullTree)
        whatLayout.addWidget(button)
        button = QRadioButton(_('Selected &branches'))
        self.whatButtons.addButton(button, NumberingScope.selectBranch)
        whatLayout.addWidget(button)
        button = QRadioButton(_('&Selection\'s children'))
        self.whatButtons.addButton(button, NumberingScope.selectChildren)
        whatLayout.addWidget(button)
        self.whatButtons.button(NumberingScope.fullTree).setChecked(True)

        rootBox = QGroupBox(_('Root Node'))
        topLayout.addWidget(rootBox)
        rootLayout = QVBoxLayout(rootBox)
        self.rootCheck = QCheckBox(_('Include top-level nodes'))
        rootLayout.addWidget(self.rootCheck)
        self.rootCheck.setChecked(True)

        noFieldBox = QGroupBox(_('Handling Nodes without Numbering '
                                       'Fields'))
        topLayout.addWidget(noFieldBox)
        noFieldLayout =  QVBoxLayout(noFieldBox)
        self.noFieldButtons = QButtonGroup(self)
        button = QRadioButton(_('&Ignore and skip'))
        self.noFieldButtons.addButton(button, NumberingNoField.ignoreNoField)
        noFieldLayout.addWidget(button)
        button = QRadioButton(_('&Restart numbers for next siblings'))
        self.noFieldButtons.addButton(button,
                                      NumberingNoField.restartAfterNoField)
        noFieldLayout.addWidget(button)
        button = QRadioButton(_('Reserve &numbers'))
        self.noFieldButtons.addButton(button, NumberingNoField.reserveNoField)
        noFieldLayout.addWidget(button)
        self.noFieldButtons.button(NumberingNoField.
                                   ignoreNoField).setChecked(True)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.numberAndClose)
        applyButton = QPushButton(_('&Apply'))
        ctrlLayout.addWidget(applyButton)
        applyButton.clicked.connect(self.updateNumbering)
        closeButton = QPushButton(_('&Close'))
        ctrlLayout.addWidget(closeButton)
        closeButton.clicked.connect(self.close)
        self.updateCommandsAvail()

    def updateCommandsAvail(self):
        """Set branch numbering available based on tree selections.
        """
        selNodes = globalref.mainControl.activeControl.currentSelectionModel()
        hasChild = False
        for node in selNodes.selectedNodes():
            if node.childList:
                hasChild = True
        self.whatButtons.button(NumberingScope.
                                selectChildren).setEnabled(hasChild)
        if not self.whatButtons.checkedButton().isEnabled():
            self.whatButtons.button(NumberingScope.fullTree).setChecked(True)

    def checkForNumberingFields(self):
        """Check that the tree formats have numbering formats.

        Return a dict of numbering field names by node format name.
        If not found, warn user.
        """
        fieldDict = (globalref.mainControl.activeControl.structure.treeFormats.
                     numberingFieldDict())
        if not fieldDict:
            QMessageBox.warning(self, _('TreeLine Numbering'),
                             _('No numbering fields were found in data types'))
        return fieldDict

    def updateNumbering(self):
        """Perform the numbering update operation.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        fieldDict = self.checkForNumberingFields()
        if fieldDict:
            control = globalref.mainControl.activeControl
            selNodes = control.currentSelectionModel().selectedNodes()
            if (self.whatButtons.checkedId() == NumberingScope.fullTree or
                len(selNodes) == 0):
                selNodes = control.structure.childList
            undo.DataUndo(control.structure.undoList, selNodes, addBranch=True)
            reserveNums = (self.noFieldButtons.checkedId() ==
                           NumberingNoField.reserveNoField)
            restartSetting = (self.noFieldButtons.checkedId() ==
                              NumberingNoField.restartAfterNoField)
            includeRoot = self.rootCheck.isChecked()
            if self.whatButtons.checkedId() == NumberingScope.selectChildren:
                levelLimit = 2
            else:
                levelLimit = sys.maxsize
            startNum = [1]
            completedClones = set()
            for node in selNodes:
                node.updateNumbering(fieldDict, startNum, levelLimit,
                                     completedClones, includeRoot,
                                     reserveNums, restartSetting)
                if not restartSetting:
                    startNum[0] += 1
            control.updateAll()
        QApplication.restoreOverrideCursor()

    def numberAndClose(self):
        """Perform the numbering update operation and close the dialog.
        """
        self.updateNumbering()
        self.close()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


menuNames = collections.OrderedDict([(N_('File Menu'), _('File')),
                                     (N_('Edit Menu'), _('Edit')),
                                     (N_('Node Menu'), _('Node')),
                                     (N_('Data Menu'), _('Data')),
                                     (N_('Tools Menu'), _('Tools')),
                                     (N_('Format Menu'), _('Format')),
                                     (N_('View Menu'), _('View')),
                                     (N_('Window Menu'), _('Window')),
                                     (N_('Help Menu'), _('Help'))])

class CustomShortcutsDialog(QDialog):
    """Dialog for customizing keyboard commands.
    """
    def __init__(self, allActions, parent=None):
        """Create a shortcuts selection dialog.

        Arguments:
            allActions -- dict of all actions from a window
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Keyboard Shortcuts'))
        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        scrollArea = QScrollArea()
        topLayout.addWidget(scrollArea)
        viewport = QWidget()
        viewLayout = QGridLayout(viewport)
        scrollArea.setWidget(viewport)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scrollArea.setWidgetResizable(True)

        self.editors = []
        for i, keyOption in enumerate(globalref.keyboardOptions.values()):
            category = menuNames.get(keyOption.category, _('No menu'))
            try:
                action = allActions[keyOption.name]
            except KeyError:
                pass
            else:
                text = '{0} > {1}'.format(category, action.toolTip())
                label = QLabel(text)
                viewLayout.addWidget(label, i, 0)
                editor = KeyLineEdit(keyOption, action, self)
                viewLayout.addWidget(editor, i, 1)
                self.editors.append(editor)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        restoreButton = QPushButton(_('&Restore Defaults'))
        ctrlLayout.addWidget(restoreButton)
        restoreButton.clicked.connect(self.restoreDefaults)
        ctrlLayout.addStretch(0)
        self.okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.editors[0].setFocus()

    def restoreDefaults(self):
        """Restore all default keyboard shortcuts.
        """
        for editor in self.editors:
            editor.loadDefaultKey()

    def accept(self):
        """Save any changes to options and actions before closing.
        """
        modified = False
        for editor in self.editors:
            if editor.modified:
                editor.saveChange()
                modified = True
        if modified:
            globalref.keyboardOptions.writeFile()
        super().accept()


class KeyLineEdit(QLineEdit):
    """Line editor for keyboad sequence entry.
    """
    usedKeySet = set()
    blankText = ' ' * 8
    def __init__(self, keyOption, action, parent=None):
        """Create a key editor.

        Arguments:
            keyOption -- the KeyOptionItem for this editor
            action -- the action to update on changes
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.keyOption = keyOption
        self.keyAction = action
        self.key = None
        self.modified = False
        self.setReadOnly(True)
        self.loadKey()

    def loadKey(self):
        """Load the initial key shortcut from the option.
        """
        key = self.keyOption.value
        if key:
            self.setKey(key)
        else:
            self.setText(KeyLineEdit.blankText)

    def loadDefaultKey(self):
        """Change to the default key shortcut from the option.

        Arguments:
            useDefault -- if True, load the default key
        """
        key = self.keyOption.defaultValue
        if key == self.key:
            return
        if key:
            self.setKey(key)
            self.modified = True
        else:
            self.clearKey(False)

    def setKey(self, key):
        """Set this editor to the given key and add to the used key set.

        Arguments:
            key - the QKeySequence to add
        """
        keyText = key.toString(QKeySequence.NativeText)
        self.setText(keyText)
        self.key = key
        KeyLineEdit.usedKeySet.add(keyText)

    def clearKey(self, staySelected=True):
        """Remove any existing key.
        """
        self.setText(KeyLineEdit.blankText)
        if staySelected:
            self.selectAll()
        if self.key:
            KeyLineEdit.usedKeySet.remove(self.key.toString(QKeySequence.
                                                            NativeText))
            self.key = None
            self.modified = True

    def saveChange(self):
        """Save any change to the option and action.
        """
        if self.modified:
            self.keyOption.setValue(self.key)
            if self.key:
                self.keyAction.setShortcut(self.key)
            else:
                self.keyAction.setShortcut(QKeySequence())

    def keyPressEvent(self, event):
        """Capture key strokes and update the editor if valid.

        Arguments:
            event -- the key press event
        """
        if event.key() in (Qt.Key_Shift, Qt.Key_Control,
                           Qt.Key_Meta, Qt.Key_Alt,
                           Qt.Key_AltGr, Qt.Key_CapsLock,
                           Qt.Key_NumLock, Qt.Key_ScrollLock,
                           Qt.Key_Pause, Qt.Key_Print,
                           Qt.Key_Cancel):
            event.ignore()
        elif event.key() in (Qt.Key_Backspace, Qt.Key_Escape):
            self.clearKey()
            event.accept()
        else:
            modifier = event.modifiers()
            if modifier & Qt.KeypadModifier:
                modifier = modifier ^ Qt.KeypadModifier
            key = QKeySequence(event.key() + int(modifier))
            if key != self.key:
                keyText = key.toString(QKeySequence.NativeText)
                if keyText not in KeyLineEdit.usedKeySet:
                    if self.key:
                        KeyLineEdit.usedKeySet.remove(self.key.
                                                   toString(QKeySequence.
                                                            NativeText))
                    self.setKey(key)
                    self.selectAll()
                    self.modified = True
                else:
                    text = _('Key {0} is already used').format(keyText)
                    QMessageBox.warning(self.parent(), 'TreeLine', text)
            event.accept()

    def contextMenuEvent(self, event):
        """Change to a context menu with a clear command.

        Arguments:
            event -- the menu event
        """
        menu = QMenu(self)
        menu.addAction(_('Clear &Key'), self.clearKey)
        menu.exec_(event.globalPos())

    def mousePressEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def mouseReleaseEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def mouseMoveEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """Capture mouse clicks to avoid selection loss.

        Arguments:
            event -- the mouse event
        """
        event.accept()

    def focusInEvent(self, event):
        """Select contents when focussed.

        Arguments:
            event -- the focus event
        """
        self.selectAll()
        super().focusInEvent(event)


class CustomToolbarDialog(QDialog):
    """Dialog for customizing toolbar buttons.
    """
    separatorString = _('--Separator--')
    def __init__(self, allActions, updateFunction, parent=None):
        """Create a toolbar buttons customization dialog.

        Arguments:
            allActions -- dict of all actions from a window
            updateFunction -- a function ref for updating window toolbars
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Customize Toolbars'))
        self.allActions = allActions
        self.updateFunction = updateFunction
        self.availableCommands = []
        self.modified = False
        self.numToolbars = 0
        self.availableCommands = []
        self.toolbarLists = []

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        gridLayout = QGridLayout()
        topLayout.addLayout(gridLayout)

        sizeBox = QGroupBox(_('Toolbar &Size'))
        gridLayout.addWidget(sizeBox, 0, 0, 1, 2)
        sizeLayout = QVBoxLayout(sizeBox)
        self.sizeCombo = QComboBox()
        sizeLayout.addWidget(self.sizeCombo)
        self.sizeCombo.addItems([_('Small Icons'), _('Large Icons')])
        self.sizeCombo.currentIndexChanged.connect(self.setModified)

        numberBox = QGroupBox(_('Toolbar Quantity'))
        gridLayout.addWidget(numberBox, 0, 2)
        numberLayout = QHBoxLayout(numberBox)
        self.quantitySpin = QSpinBox()
        numberLayout.addWidget(self.quantitySpin)
        self.quantitySpin.setRange(0, 20)
        numberlabel = QLabel(_('&Toolbars'))
        numberLayout.addWidget(numberlabel)
        numberlabel.setBuddy(self.quantitySpin)
        self.quantitySpin.valueChanged.connect(self.changeQuantity)

        availableBox = QGroupBox(_('A&vailable Commands'))
        gridLayout.addWidget(availableBox, 1, 0)
        availableLayout = QVBoxLayout(availableBox)
        menuCombo = QComboBox()
        availableLayout.addWidget(menuCombo)
        menuCombo.addItems([_(name) for name in menuNames.keys()])
        menuCombo.currentIndexChanged.connect(self.updateAvailableCommands)

        self.availableListWidget = QListWidget()
        availableLayout.addWidget(self.availableListWidget)

        buttonLayout = QVBoxLayout()
        gridLayout.addLayout(buttonLayout, 1, 1)
        self.addButton = QPushButton('>>')
        buttonLayout.addWidget(self.addButton)
        self.addButton.setMaximumWidth(self.addButton.sizeHint().height())
        self.addButton.clicked.connect(self.addTool)

        self.removeButton = QPushButton('<<')
        buttonLayout.addWidget(self.removeButton)
        self.removeButton.setMaximumWidth(self.removeButton.sizeHint().
                                          height())
        self.removeButton.clicked.connect(self.removeTool)

        toolbarBox = QGroupBox(_('Tool&bar Commands'))
        gridLayout.addWidget(toolbarBox, 1, 2)
        toolbarLayout = QVBoxLayout(toolbarBox)
        self.toolbarCombo = QComboBox()
        toolbarLayout.addWidget(self.toolbarCombo)
        self.toolbarCombo.currentIndexChanged.connect(self.
                                                      updateToolbarCommands)

        self.toolbarListWidget = QListWidget()
        toolbarLayout.addWidget(self.toolbarListWidget)
        self.toolbarListWidget.currentRowChanged.connect(self.
                                                         setButtonsAvailable)

        moveLayout = QHBoxLayout()
        toolbarLayout.addLayout(moveLayout)
        self.moveUpButton = QPushButton(_('Move &Up'))
        moveLayout.addWidget(self.moveUpButton)
        self.moveUpButton.clicked.connect(self.moveUp)
        self.moveDownButton = QPushButton(_('Move &Down'))
        moveLayout.addWidget(self.moveDownButton)
        self.moveDownButton.clicked.connect(self.moveDown)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        restoreButton = QPushButton(_('&Restore Defaults'))
        ctrlLayout.addWidget(restoreButton)
        restoreButton.clicked.connect(self.restoreDefaults)
        ctrlLayout.addStretch()
        self.okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        self.applyButton = QPushButton(_('&Apply'))
        ctrlLayout.addWidget(self.applyButton)
        self.applyButton.clicked.connect(self.applyChanges)
        self.applyButton.setEnabled(False)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

        self.updateAvailableCommands(0)
        self.loadToolbars()

    def setModified(self):
        """Set modified flag and make apply button available.
        """
        self.modified = True
        self.applyButton.setEnabled(True)

    def setButtonsAvailable(self):
        """Enable or disable buttons based on toolbar list state.
        """
        toolbarNum = numCommands = commandNum = 0
        if self.numToolbars:
            toolbarNum = self.toolbarCombo.currentIndex()
            numCommands = len(self.toolbarLists[toolbarNum])
            if self.toolbarLists[toolbarNum]:
                commandNum = self.toolbarListWidget.currentRow()
        self.addButton.setEnabled(self.numToolbars > 0)
        self.removeButton.setEnabled(self.numToolbars and numCommands)
        self.moveUpButton.setEnabled(self.numToolbars and numCommands > 1 and
                                     commandNum > 0)
        self.moveDownButton.setEnabled(self.numToolbars and numCommands > 1 and
                                       commandNum < numCommands - 1)

    def loadToolbars(self, defaultOnly=False):
        """Load all toolbar data from options.

        Arguments:
            defaultOnly -- if True, load default settings
        """
        size = (globalref.toolbarOptions['ToolbarSize'] if not defaultOnly else
                globalref.toolbarOptions.getDefaultValue('ToolbarSize'))
        self.sizeCombo.blockSignals(True)
        if size < 24:
            self.sizeCombo.setCurrentIndex(0)
        else:
            self.sizeCombo.setCurrentIndex(1)
        self.sizeCombo.blockSignals(False)
        self.numToolbars = (globalref.toolbarOptions['ToolbarQuantity'] if not
                            defaultOnly else globalref.toolbarOptions.
                            getDefaultValue('ToolbarQuantity'))
        self.quantitySpin.blockSignals(True)
        self.quantitySpin.setValue(self.numToolbars)
        self.quantitySpin.blockSignals(False)
        self.toolbarLists = []
        commands = (globalref.toolbarOptions['ToolbarCommands'] if not
                    defaultOnly else globalref.toolbarOptions.
                    getDefaultValue('ToolbarCommands'))
        self.toolbarLists = [cmd.split(',') for cmd in commands]
        # account for toolbar quantity mismatch (should not happen)
        del self.toolbarLists[self.numToolbars:]
        while len(self.toolbarLists) < self.numToolbars:
            self.toolbarLists.append([])
        self.updateToolbarCombo()

    def updateToolbarCombo(self):
        """Fill combo with toolbar numbers for current quantity.
        """
        self.toolbarCombo.clear()
        if self.numToolbars:
            self.toolbarCombo.addItems(['Toolbar {0}'.format(num + 1) for
                                        num in range(self.numToolbars)])
        else:
            self.toolbarListWidget.clear()
            self.setButtonsAvailable()

    def updateAvailableCommands(self, menuNum):
        """Fill in available command list for given menu.

        Arguments:
            menuNum -- the index of the current menu selected
        """
        menuName = list(menuNames.keys())[menuNum]
        self.availableCommands = []
        self.availableListWidget.clear()
        for option in globalref.keyboardOptions.values():
            if option.category == menuName:
                action = self.allActions[option.name]
                icon = action.icon()
                if not icon.isNull():
                    self.availableCommands.append(option.name)
                    QListWidgetItem(icon, action.toolTip(),
                                          self.availableListWidget)
        QListWidgetItem(CustomToolbarDialog.separatorString,
                              self.availableListWidget)
        self.availableListWidget.setCurrentRow(0)

    def updateToolbarCommands(self, toolbarNum):
        """Fill in toolbar commands for given toolbar.

        Arguments:
            toolbarNum -- the number of the toolbar to update
        """
        self.toolbarListWidget.clear()
        if self.numToolbars == 0:
            return
        for command in self.toolbarLists[toolbarNum]:
            if command:
                action = self.allActions[command]
                QListWidgetItem(action.icon(), action.toolTip(),
                                      self.toolbarListWidget)
            else:  # separator
                QListWidgetItem(CustomToolbarDialog.separatorString,
                                      self.toolbarListWidget)
        if self.toolbarLists[toolbarNum]:
            self.toolbarListWidget.setCurrentRow(0)
        self.setButtonsAvailable()

    def changeQuantity(self, qty):
        """Change the toolbar quantity based on a spin box signal.

        Arguments:
            qty -- the new toolbar quantity
        """
        self.numToolbars = qty
        while qty > len(self.toolbarLists):
            self.toolbarLists.append([])
        self.updateToolbarCombo()
        self.setModified()

    def addTool(self):
        """Add the selected command to the current toolbar.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        try:
            command = self.availableCommands[self.availableListWidget.
                                             currentRow()]
            action = self.allActions[command]
            item = QListWidgetItem(action.icon(), action.toolTip())
        except IndexError:
            command = ''
            item = QListWidgetItem(CustomToolbarDialog.separatorString)
        if self.toolbarLists[toolbarNum]:
            pos = self.toolbarListWidget.currentRow() + 1
        else:
            pos = 0
        self.toolbarLists[toolbarNum].insert(pos, command)
        self.toolbarListWidget.insertItem(pos, item)
        self.toolbarListWidget.setCurrentRow(pos)
        self.toolbarListWidget.scrollToItem(item)
        self.setModified()

    def removeTool(self):
        """Remove the selected command from the current toolbar.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        pos = self.toolbarListWidget.currentRow()
        del self.toolbarLists[toolbarNum][pos]
        self.toolbarListWidget.takeItem(pos)
        if self.toolbarLists[toolbarNum]:
            if pos == len(self.toolbarLists[toolbarNum]):
                pos -= 1
            self.toolbarListWidget.setCurrentRow(pos)
        self.setModified()

    def moveUp(self):
        """Raise the selected command.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        pos = self.toolbarListWidget.currentRow()
        command = self.toolbarLists[toolbarNum].pop(pos)
        self.toolbarLists[toolbarNum].insert(pos - 1, command)
        item = self.toolbarListWidget.takeItem(pos)
        self.toolbarListWidget.insertItem(pos - 1, item)
        self.toolbarListWidget.setCurrentRow(pos - 1)
        self.toolbarListWidget.scrollToItem(item)
        self.setModified()

    def moveDown(self):
        """Lower the selected command.
        """
        toolbarNum = self.toolbarCombo.currentIndex()
        pos = self.toolbarListWidget.currentRow()
        command = self.toolbarLists[toolbarNum].pop(pos)
        self.toolbarLists[toolbarNum].insert(pos + 1, command)
        item = self.toolbarListWidget.takeItem(pos)
        self.toolbarListWidget.insertItem(pos + 1, item)
        self.toolbarListWidget.setCurrentRow(pos + 1)
        self.toolbarListWidget.scrollToItem(item)
        self.setModified()

    def restoreDefaults(self):
        """Restore all default toolbar settings.
        """
        self.loadToolbars(True)
        self.setModified()

    def applyChanges(self):
        """Apply any changes from the dialog.
        """
        size = 16 if self.sizeCombo.currentIndex() == 0 else 32
        globalref.toolbarOptions.changeValue('ToolbarSize', size)
        globalref.toolbarOptions.changeValue('ToolbarQuantity',
                                             self.numToolbars)
        del self.toolbarLists[self.numToolbars:]
        commands = [','.join(cmds) for cmds in self.toolbarLists]
        globalref.toolbarOptions.changeValue('ToolbarCommands', commands)
        globalref.toolbarOptions.writeFile()
        self.modified = False
        self.applyButton.setEnabled(False)
        self.updateFunction()

    def accept(self):
        """Apply changes and close the dialog.
        """
        if self.modified:
            self.applyChanges()
        super().accept()


class CustomFontData:
    """Class to store custom font settings.

    Acts as a stand-in for PrintData class in the font page of the dialog.
    """
    def __init__(self, fontOption, useAppDefault=True):
        """Initialize the font data.

        Arguments:
            fontOption -- the name of the font setting to retrieve
            useAppDefault -- use app default if true, o/w use sys default
        """
        self.fontOption = fontOption
        if useAppDefault:
            self.defaultFont = QTextDocument().defaultFont()
        else:
            self.defaultFont = QFont(globalref.mainControl.systemFont)
        self.useDefaultFont = True
        self.mainFont = QFont(self.defaultFont)
        fontName = globalref.miscOptions[self.fontOption]
        if fontName:
            self.mainFont.fromString(fontName)
            self.useDefaultFont = False

    def recordChanges(self):
        """Record the updated font info to the option settings.
        """
        if self.useDefaultFont:
            globalref.miscOptions.changeValue(self.fontOption, '')
        else:
            globalref.miscOptions.changeValue(self.fontOption,
                                              self.mainFont.toString())


class CustomFontDialog(QDialog):
    """Dialog for selecting custom fonts.

    Uses the print setup dialog's font page for the details.
    """
    updateRequired = pyqtSignal()
    def __init__(self, parent=None):
        """Create a font customization dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Customize Fonts'))

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        self.tabs = QTabWidget()
        topLayout.addWidget(self.tabs)
        self.tabs.setUsesScrollButtons(False)
        self.tabs.currentChanged.connect(self.updateTabDefault)

        self.pages = []
        defaultLabel = _('&Use system default font')
        appFontPage = printdialogs.FontPage(CustomFontData('AppFont', False),
                                            defaultLabel)
        self.pages.append(appFontPage)
        self.tabs.addTab(appFontPage, _('App Default Font'))
        defaultLabel = _('&Use app default font')
        treeFontPage = printdialogs.FontPage(CustomFontData('TreeFont'),
                                             defaultLabel)
        self.pages.append(treeFontPage)
        self.tabs.addTab(treeFontPage, _('Tree View Font'))
        outputFontPage = printdialogs.FontPage(CustomFontData('OutputFont'),
                                               defaultLabel)
        self.pages.append(outputFontPage)
        self.tabs.addTab(outputFontPage, _('Output View Font'))
        editorFontPage = printdialogs.FontPage(CustomFontData('EditorFont'),
                                               defaultLabel)
        self.pages.append(editorFontPage)
        self.tabs.addTab(editorFontPage, _('Editor View Font'))

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        self.okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        self.applyButton = QPushButton(_('&Apply'))
        ctrlLayout.addWidget(self.applyButton)
        self.applyButton.clicked.connect(self.applyChanges)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def updateTabDefault(self):
        """Update the default font on the newly shown page.
        """
        appFontWidget = self.tabs.widget(0)
        currentWidget = self.tabs.currentWidget()
        if appFontWidget is not currentWidget:
            if appFontWidget.defaultCheck.isChecked():
                defaultFont = QFont(globalref.mainControl.systemFont)
            else:
                defaultFont = appFontWidget.readFont()
            currentWidget.printData.defaultFont = defaultFont
            if currentWidget.defaultCheck.isChecked():
                currentWidget.printData.mainFont = QFont(defaultFont)
                currentWidget.currentFont = currentWidget.printData.mainFont
                currentWidget.setFont(defaultFont)

    def applyChanges(self):
        """Apply any changes from the dialog.
        """
        modified = False
        for page in self.pages:
            if page.saveChanges():
                page.printData.recordChanges()
                modified = True
        if modified:
            globalref.miscOptions.writeFile()
            self.updateRequired.emit()

    def accept(self):
        """Apply changes and close the dialog.
        """
        self.applyChanges()
        super().accept()


class AboutDialog(QDialog):
    """Show program info in a text box.
    """
    def __init__(self, title, textLines, icon=None, parent=None):
        """Create the dialog.

        Arguments:
            title -- the window title text
            textLines -- a list of lines to show
            icon -- an icon to show if given
            parent -- the parent window
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(title)

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        mainLayout = QHBoxLayout()
        topLayout.addLayout(mainLayout)
        iconLabel = QLabel()
        iconLabel.setPixmap(icon.pixmap(128, 128))
        mainLayout.addWidget(iconLabel)
        textBox = QPlainTextEdit()
        textBox.setReadOnly(True)
        textBox.setWordWrapMode(QTextOption.NoWrap)
        textBox.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        textBox.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        text = '\n'.join(textLines)
        textBox.setPlainText(text)
        size = textBox.fontMetrics().size(0, text)
        size.setHeight(size.height() + 10)
        size.setWidth(size.width() + 10)
        textBox.setMinimumSize(size)
        mainLayout.addWidget(textBox)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
