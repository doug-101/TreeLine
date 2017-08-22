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
            if fileChange and window.isFiltering():
                filterView = window.treeFilterView
                self.textEntry.setText(filterView.filterStr)
                self.whatButtons.button(filterView.filterWhat).setChecked(True)
                self.howButtons.button(filterView.filterHow).setChecked(True)
            self.filterButton.setEnabled(hasEntry)
            self.endFilterButton.setEnabled(window.isFiltering())

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
        window = globalref.mainControl.activeControl.activeWindow
        filterView = window.treeFilterView
        filterView.filterWhat = self.whatButtons.checkedId()
        filterView.filterHow = self.howButtons.checkedId()
        filterView.filterStr = self.textEntry.text()
        filterView.updateContents()
        window.treeStack.setCurrentWidget(filterView)
        self.updateAvail()

    def endFilter(self):
        """Stop filtering nodes.
        """
        window = globalref.mainControl.activeControl.activeWindow
        window.treeStack.setCurrentWidget(window.treeView)
        self.updateAvail()
        globalref.mainControl.currentStatusBar().clearMessage()

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
