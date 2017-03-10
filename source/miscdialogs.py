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

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                             QCheckBox, QComboBox, QDialog, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPushButton, QRadioButton, QScrollArea, QSpinBox,
                             QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)


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
            button = QRadioButton(text)
            button.returnValue = value
            groupLayout.addWidget(button)
            self.buttonGroup.addButton(button)
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
