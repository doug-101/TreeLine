#!/usr/bin/env python3

#******************************************************************************
# options.py, provides a class to manage config options
#
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from collections import OrderedDict
import sys
import re
import os.path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                             QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QRadioButton, QSpinBox, QVBoxLayout)
import miscdialogs

multipleSpaceRegEx = re.compile(r' {2,}')


class StringOptionItem:
    """Class to store and control a string-based config option entry.

    Stores the name, value, category and description, provides validation,
    config file output and dialog controls.
    """
    def __init__(self, optionDict, name, value, emptyOK=True,
                 stripSpaces=False, category='', description='', columnNum=0):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- the string value
            emptyOK -- if False, does not allow empty string
            stripSpaces -- if True, remove leading, trailing & double spaces
            category -- a string for the option group this belongs to
            description -- a string for use in the control dialog
            columnNum -- the column position for this control in the dialog
        """
        self.name = name
        self.category = category
        self.description = description
        self.columnNum = columnNum
        self.emptyOK = emptyOK
        self.stripSpaces = stripSpaces
        self.dialogControl = None
        self.value = None
        self.setValue(value)
        self.defaultValue = self.value
        optionDict[name] = self

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- the string value to set
        """
        value = str(value)
        if self.stripSpaces:
            value = multipleSpaceRegEx.sub(' ', value.strip())
        if value != self.value and (value or self.emptyOK):
            self.value = value
            return True
        if self.value == None:
            raise ValueError
        return False

    def valueString(self):
        """Return a string representation of the value.
        """
        return str(self.value)

    def outputLine(self, padding=20):
        """Return an output line for writing to a config file.

        Arguments:
            padding -- the width to reserve for the name key
        """
        return '{0:{1}}{2}\n'.format(self.name, padding, self.valueString())

    def addDialogControl(self, rowLayout, currentGroupBox):
        """Add the labels and controls to a dialog box for this option item.

        Uses the current group box if the category matches, otherwise
        starts a new one.  Returns the current group box.
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        groupBox = self.getGroupBox(rowLayout, currentGroupBox)
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        label = QLabel(self.description, groupBox)
        gridLayout.addWidget(label, row, 0)
        self.dialogControl = QLineEdit(self.value, groupBox)
        gridLayout.addWidget(self.dialogControl, row, 1)
        return groupBox

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.text())

    def getGroupBox(self, rowLayout, currentGroupBox):
        """Return the group box for use with this option item category.

        Group box is same if category matches, creates one otherwise.
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        if currentGroupBox and currentGroupBox.title() == self.category:
            return currentGroupBox
        newGroupBox = QGroupBox(self.category,
                                      rowLayout.parentWidget())
        rowLayout.addWidget(newGroupBox)
        QGridLayout(newGroupBox)
        return newGroupBox


class IntOptionItem(StringOptionItem):
    """Class to store and control an integer-based config option entry.

    Stores the name, value, category and description, provides validation,
    config file output and dialog controls.
    """
    def __init__(self, optionDict, name, value, minimum=None, maximum=None,
                 category='', description='', columnNum=0):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- a numeric or string-based value
            minimum -- optional minimum value
            maximum -- optional maximum value
            category -- a string for the option group this belongs to
            description -- a string for use in the control dialog
            columnNum -- the column position for this control in the dialog
        """
        self.minimum = minimum
        self.maximum = maximum
        super().__init__(optionDict, name, value, False, False, category,
                         description, columnNum)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- a numeric or string-based value to set
        """
        try:
            value = int(value)
            if self.minimum != None and value < self.minimum:
                raise ValueError
            if self.maximum != None and value > self.maximum:
                raise ValueError
        except ValueError:
            if self.value == None:
                raise
            return False
        if value != self.value:
            self.value = value
            return True
        return False

    def addDialogControl(self, rowLayout, currentGroupBox):
        """Add the labels and controls to a dialog box for this option item.

        Uses the current group box if the category matches, otherwise
        starts a new one.  Returns the current group box.
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        groupBox = self.getGroupBox(rowLayout, currentGroupBox)
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        label = QLabel(self.description, groupBox)
        gridLayout.addWidget(label, row, 0)
        self.dialogControl = QSpinBox(groupBox)
        self.dialogControl.setValue(self.value)
        if self.minimum != None:
            self.dialogControl.setMinimum(self.minimum)
        if self.maximum != None:
            self.dialogControl.setMaximum(self.maximum)
        gridLayout.addWidget(self.dialogControl, row, 1)
        return groupBox

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.value())


class FloatOptionItem(StringOptionItem):
    """Class to store and control a float-based config option entry.

    Stores the name, value, category and description, provides validation,
    config file output and dialog controls.
    """
    def __init__(self, optionDict, name, value, minimum=None, maximum=None,
                 category='', description='', columnNum=0):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- a numeric or string-based value
            minimum -- optional minimum value
            maximum -- optional maximum value
            category -- a string for the option group this belongs to
            description -- a string for use in the control dialog
            columnNum -- the column position for this control in the dialog
        """
        self.minimum = minimum
        self.maximum = maximum
        super().__init__(optionDict, name, value, False, False, category,
                         description, columnNum)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- a numeric or string-based value to set
        """
        try:
            value = float(value)
            if self.minimum != None and value < self.minimum:
                raise ValueError
            if self.maximum != None and value > self.maximum:
                raise ValueError
        except ValueError:
            if self.value == None:
                raise
            return False
        if value != self.value:
            self.value = value
            return True
        return False

    def addDialogControl(self, rowLayout, currentGroupBox):
        """Add the labels and controls to a dialog box for this option item.

        Uses the current group box if the category matches, otherwise
        starts a new one.  Returns the current group box.
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        groupBox = self.getGroupBox(rowLayout, currentGroupBox)
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        label = QLabel(self.description, groupBox)
        gridLayout.addWidget(label, row, 0)
        self.dialogControl = QDoubleSpinBox(groupBox)
        self.dialogControl.setValue(self.value)
        if self.minimum != None:
            self.dialogControl.setMinimum(self.minimum)
        if self.maximum != None:
            self.dialogControl.setMaximum(self.maximum)
        gridLayout.addWidget(self.dialogControl, row, 1)
        return groupBox

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.value())


class BoolOptionItem(StringOptionItem):
    """Class to store and control a boolean config option entry.

    Stores the name, value, category and description, provides validation,
    config file output and dialog controls.
    """
    def __init__(self, optionDict, name, value, category='', description='',
                 columnNum=0):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- the boolean or string value
            category -- a string for the option group this belongs to
            description -- a string for use in the control dialog
            columnNum -- the column position for this control in the dialog
        """
        super().__init__(optionDict, name, value, False, False, category,
                         description, columnNum)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- a boolean or string-based value to set
        """
        if hasattr(value, 'lower'):
            if value.lower() in ('yes', 'y', 'true'):
                value = True
            elif value.lower() in ('no', 'n', 'false'):
                value = False
        else:
            value = bool(value)
        if value in (True, False) and value != self.value:
            self.value = value
            return True
        if self.value == None:
            raise ValueError
        return False

    def valueString(self):
        """Return a string representation of the value.
        """
        return 'yes' if self.value else 'no'

    def addDialogControl(self, rowLayout, currentGroupBox):
        """Add the labels and controls to a dialog box for this option item.

        Uses the current group box if the category matches, otherwise
        starts a new one.  Returns the current group box.
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        groupBox = self.getGroupBox(rowLayout, currentGroupBox)
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        self.dialogControl = QCheckBox(self.description, groupBox)
        self.dialogControl.setChecked(self.value)
        gridLayout.addWidget(self.dialogControl, row, 0, 1, 2)
        return groupBox

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.isChecked())


class ListOptionItem(StringOptionItem):
    """Class to store and control a pull-down list config option entry.

    Stores the name, value, category and description, provides validation,
    config file output and dialog controls.
    """
    def __init__(self, optionDict, name, value, choices, category='',
                 description='', columnNum=0):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- the string value
            choices -- a list of acceptable entries
            category -- a string for the option group this belongs to
            description -- a string for use in the control dialog
            columnNum -- the column position for this control in the dialog
        """
        self.choices = choices
        super().__init__(optionDict, name, value, False, False, category,
                         description, columnNum)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- the string value to set
        """
        value = str(value)
        if value in self.choices and value != self.value:
            self.value = value
            return True
        if self.value == None:
            raise ValueError
        return False

    def addDialogControl(self, rowLayout, currentGroupBox):
        """Add the labels and controls to a dialog box for this option item.

        Uses the current group box if the category matches, otherwise
        starts a new one.  Returns the current group box.
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        groupBox = self.getGroupBox(rowLayout, currentGroupBox)
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        label = QLabel(self.description, groupBox)
        gridLayout.addWidget(label, row, 0)
        self.dialogControl = QComboBox(groupBox)
        self.dialogControl.addItems(self.choices)
        self.dialogControl.setCurrentIndex(self.choices.index(self.value))
        gridLayout.addWidget(self.dialogControl, row, 1)
        return groupBox

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.currentText())


class ChoiceOptionItem(StringOptionItem):
    """Class to store and control a radio button choice config option entry.

    Stores the name, value, category and description, provides validation,
    config file output and dialog controls.
    """
    def __init__(self, optionDict, name, value, choices, category='',
                 columnNum=0):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- the string value
            choices -- a list of acceptable entries
            category -- a string for the option group this belongs to
            columnNum -- the column position for this control in the dialog
        """
        self.choices = choices
        super().__init__(optionDict, name, value, False, False, category, '',
                         columnNum)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- the string value to set
        """
        value = str(value)
        if value in self.choices and value != self.value:
            self.value = value
            return True
        if self.value == None:
            raise ValueError
        return False

    def addDialogControl(self, rowLayout, currentGroupBox):
        """Add the labels and controls to a dialog box for this option item.

        Always starts a new group box, returns None (group not reused).
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        groupBox = QGroupBox(self.category, rowLayout.parentWidget())
        rowLayout.addWidget(groupBox)
        QGridLayout(groupBox)
        gridLayout = groupBox.layout()
        self.dialogControl = QButtonGroup(groupBox)
        row = 0
        for choice in self.choices:
            button = QRadioButton(choice, groupBox)
            self.dialogControl.addButton(button)
            gridLayout.addWidget(button, row, 0, 1, 2)
            row += 1
        return None

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.checkedButton().text())


class KeyOptionItem(StringOptionItem):
    """Class to store and control a keyboard key based config option entry.

    Stores the name, value, category and description, provides validation,
    config file output and dialog controls.
    """
    def __init__(self, optionDict, name, value, category='', description='',
                 columnNum=0):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- a numeric or string-based value
            category -- a string for the option group this belongs to
            description -- a string for use in the control dialog
            columnNum -- the column position for this control in the dialog
        """
        super().__init__(optionDict, name, value, True, False, category,
                         description, columnNum)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- a numeric or string-based value to set
        """
        key = QKeySequence(value)
        if value and key.isEmpty():
            if self.value == None:
                raise ValueError
            return False
        if value != self.value:
            self.value = key
            return True
        return False

    def valueString(self):
        """Return a string representation of the value.
        """
        return self.value.toString()

    def addDialogControl(self, rowLayout, currentGroupBox):
        """Add the labels and controls to a dialog box for this option item.

        Not implemented yet (needed here?).
        Returns the current group box.
        Arguments:
            rowLayout -- the vertical box layout holding the group boxes
            currentGroupBox -- the currently used group box
        """
        return currentGroupBox

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Not implemented yet (needed here?).
        Return True if successfully set.
        """
        return False


class Options(OrderedDict):
    """Class to store and control the config options for a program.
    """
    basePath = ''
    def __init__(self, fileName='', progName='', version='', coDirName=''):
        """Initialize and set the path to the config file.

        Creates the path dir structure if necessary (if fileName is given).
        On Windows, uses the module path's config directory if it exists.
        Arguments:
            fileName -- the config file name, excluding the extension
            progName -- the program name, for dialog headings & config dir name
            version -- a version string, for config dir names
            coDirName -- the company name for the config dir in Windows OS
        """
        super().__init__()
        self.modified = False
        self.path = ''

        if not fileName:
            return    # no storage without fileName (temporary options only)
        appDirName = '{0}-{1}'.format(progName.lower(), version)
        if sys.platform.startswith('win'):    # Windows
            fileNameSuffix = '.ini'
            if not Options.basePath:
                userPath = os.path.join(os.environ.get('APPDATA', ''),
                                        coDirName, appDirName)
        else:    # Linux, etc.
            fileNameSuffix = 'rc'
            if not Options.basePath:
                userPath = os.path.join(os.environ.get('HOME', ''),
                                        '.' + appDirName)
        if not Options.basePath:
            if os.path.exists(userPath):
                Options.basePath = userPath
            else:
                modPath = os.path.dirname(os.path.abspath(sys.path[0]))
                modConfigPath = os.path.join(modPath, 'config')
                if os.path.exists(modConfigPath):
                    Options.basePath = modConfigPath
                elif os.access(modPath, os.W_OK):
                    dialog = miscdialogs.RadioChoiceDialog(progName,
                              _('Choose configuration file location'),
                              [(_('User\'s home directory (recommended)'), 0),
                               (_('Program directory (for portable use)'), 1)])
                    if dialog.exec_() != QDialog.Accepted:
                        sys.exit(0)
                    if dialog.selectedButton() == 1:
                        Options.basePath = modConfigPath
                if not Options.basePath:
                    Options.basePath = userPath
            try:
                if not os.path.exists(Options.basePath):
                    os.makedirs(Options.basePath)
                iconPath = os.path.join(Options.basePath, 'icons')
                if not os.path.exists(iconPath):
                    os.makedirs(iconPath)
                templatePath = os.path.join(Options.basePath, 'templates')
                if not os.path.exists(templatePath):
                    os.makedirs(templatePath)
                pluginPath = os.path.join(Options.basePath, 'plugins')
                if not os.path.exists(pluginPath):
                    os.makedirs(pluginPath)
            except OSError:
                Options.basePath = ''
        if Options.basePath:
            self.path = os.path.join(Options.basePath,
                                     fileName + fileNameSuffix)

    def getValue(self, name, defaultValue=False):
        """Return a value from the given option key.

        Arguments:
            name -- the string key for the option
            defaultValue -- if True, return the default value, not current one
        """
        if not defaultValue:
            return self[name].value
        return self[name].defaultValue

    def getDefaultValue(self, name):
        """Return the initially set default value from the given option key.

        Arguments:
            name -- the string key for the option
        """
        return self[name].defaultValue

    def changeValue(self, name, value):
        """Set a new value for the given option key.

        Return True if sucessful.
        Arguments:
            name -- the string key for the option
            value -- a value or a string defining the value
        """
        if self[name].setValue(value):
            self.modified = True
            return True
        return False

    def removeValue(self, name):
        """Remove the value from the option list if possible.

        If not, fail silently.
        Arguments:
            name -- the string key for the option to be removed
        """
        try:
            del self[name]
        except KeyError:
            return
        self.modified = True

    def readFile(self):
        """Read config options from the file on self.path.

        Create the file if it isn't found.
        Only updates existing config items.
        """
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                lastCategory = ''
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            name, value = line.split(None, 1)
                        except ValueError:
                            name = line
                            value = ''
                        try:
                            self[name].setValue(value)
                            lastCategory = self[name].category
                        except KeyError:
                            # create a blank default entry if none exists
                            StringOptionItem(self, name, '', True, False,
                                             lastCategory)
                            self[name].setValue(value)
        except IOError:
            self.writeFile()

    def writeFile(self):
        """Write current options to the file on self.path.

        Raises IOError on failure.
        """
        with open(self.path, 'w', encoding='utf-8') as f:
            padding = max(len(option.name) for option in self.values()) + 2
            prevCategory = ''
            for option in self.values():
                if option.category and option.category != prevCategory:
                    f.write('\n# {}:\n'.format(option.category))
                    prevCategory = option.category
                f.write(option.outputLine(padding))
        self.modified = False


class OptionDialog(QDialog):
    """Provides a dialog with controls for all options in an Options instance.
    """
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        columnLayout = QHBoxLayout()
        topLayout.addLayout(columnLayout)
        rowLayout = QVBoxLayout()
        columnLayout.addLayout(rowLayout)
        groupBox = None
        for option in self.options.values():
            if option.columnNum > columnLayout.count() - 1:
                rowLayout = QVBoxLayout()
                columnLayout.addLayout(rowLayout)
            groupBox = option.addDialogControl(rowLayout, groupBox)

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
        """Updates the options from the controls when the OK button is pressed.
        """
        for option in self.options.values():
            if option.updateFromDialog():
                self.options.modified = True
        super().accept()
