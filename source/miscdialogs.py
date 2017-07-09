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
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                             QCheckBox, QComboBox, QDialog, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPushButton, QRadioButton, QScrollArea, QSpinBox,
                             QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)
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
            if value:
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
