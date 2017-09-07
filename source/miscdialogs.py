#!/usr/bin/env python3

#******************************************************************************
# miscdialogs.py, provides classes for various control dialogs
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import enum
import re
import sys
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                             QCheckBox, QComboBox, QDialog, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPushButton, QRadioButton, QScrollArea, QSpinBox,
                             QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)
import undo
import globalref


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
        self.textEntry.textEdited.connect(self.updateAvail)
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
            selSpots = self.structure.rootSpots()
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
            undo.BranchUndo(control.structure.undoList, selNodes)
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
