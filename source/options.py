#!/usr/bin/env python3

#******************************************************************************
# options.py, provides a class to manage config options
#
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from collections import OrderedDict
import sys
import re
import pathlib
import os.path
import json
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

    def storedValue(self):
        """Return the value to be stored in the JSON file.
        """
        return self.value

    def addDialogControl(self, groupBox):
        """Add the labels and controls to a dialog box for this option item.

        Arguments:
            groupBox -- the current group box
        """
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        label = QLabel(self.description, groupBox)
        gridLayout.addWidget(label, row, 0)
        self.dialogControl = QLineEdit(self.value, groupBox)
        gridLayout.addWidget(self.dialogControl, row, 1)

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.text())


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

    def addDialogControl(self, groupBox):
        """Add the labels and controls to a dialog box for this option item.

        Arguments:
            groupBox -- the current group box
        """
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

    def addDialogControl(self, groupBox):
        """Add the labels and controls to a dialog box for this option item.

        Arguments:
            groupBox -- the current group box
        """
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

    def addDialogControl(self, groupBox):
        """Add the labels and controls to a dialog box for this option item.

        Arguments:
            groupBox -- the current group box
        """
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        self.dialogControl = QCheckBox(self.description, groupBox)
        self.dialogControl.setChecked(self.value)
        gridLayout.addWidget(self.dialogControl, row, 0, 1, 2)

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

    def addDialogControl(self, groupBox):
        """Add the labels and controls to a dialog box for this option item.

        Arguments:
            groupBox -- the current group box
        """
        gridLayout = groupBox.layout()
        row = gridLayout.rowCount()
        label = QLabel(self.description, groupBox)
        gridLayout.addWidget(label, row, 0)
        self.dialogControl = QComboBox(groupBox)
        self.dialogControl.addItems(self.choices)
        self.dialogControl.setCurrentIndex(self.choices.index(self.value))
        gridLayout.addWidget(self.dialogControl, row, 1)

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

    def addDialogControl(self, groupBox):
        """Add the labels and controls to a dialog box for this option item.

        Arguments:
            groupBox -- the current group box
        """
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

    def updateFromDialog(self):
        """Set the value of this item from the dialog contents.

        Return True if successfully set.
        """
        return self.setValue(self.dialogControl.checkedButton().text())


class KeyOptionItem(StringOptionItem):
    """Class to store and control a keyboard key based config option entry.

    Stores the name, value and category, provides validation and config file
    output.
    """
    def __init__(self, optionDict, name, value, category=''):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- a numeric or string-based value
            category -- a string for the option group this belongs to
        """
        super().__init__(optionDict, name, value, True, False, category)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- a key string value to set
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

    def storedValue(self):
        """Return the value to be stored in the JSON file.
        """
        return self.value.toString()


class DataListOptionItem(StringOptionItem):
    """Class to store an arbitrary length list containing various data.

    Stores the name and value, provides validation and config file output.
    """
    def __init__(self, optionDict, name, value):
        """Set the parameters and initial value and add to optionDict.

        Raises a ValueError if initial validation fails.
        Arguments:
            optionDict -- a dictionary to add this option item to
            name -- the string key for the option
            value -- a list containg other basic data types
        """
        super().__init__(optionDict, name, value)

    def setValue(self, value):
        """Sets the value and validates, returns True if OK.

        Returns False if validation fails but the old value is OK,
        or if the value is unchanged.
        Raises a ValueError if validation fails without an old value.
        Arguments:
            value -- a list containg other basic data types
        """
        if isinstance(value, list) and value != self.value:
            self.value = value
            return True
        if self.value == None:
            raise ValueError
        return False


class Options(OrderedDict):
    """Class to store and control the config options for a program.
    """
    basePath = None
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
        self.path = pathlib.Path()

        if not fileName:
            return    # no storage without fileName (temporary options only)
        if not version:
            version = '0'
        appDirName = '{0}-{1}'.format(progName.lower(), version)
        fileNameSuffix = '.ini' if sys.platform.startswith('win') else 'rc'

        if not Options.basePath and progName and coDirName:
            if sys.platform.startswith('win'):    # Windows
                userPath = (pathlib.Path(os.environ.get('APPDATA', '')) /
                            coDirName / appDirName)
            else:    # Linux, etc.
                userPath = (pathlib.Path(os.path.expanduser('~')) /
                            ('.' + appDirName))
            if userPath.is_dir():
                Options.basePath = userPath
            else:
                modPath = pathlib.Path(sys.path[0]).resolve()
                if modPath.is_file():
                    modPath = modPath.parent  # for frozen binary
                modConfigPath = modPath / 'config'
                if modConfigPath.is_dir():
                    Options.basePath = modConfigPath
                elif os.access(str(modPath), os.W_OK):
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
                if not Options.basePath.is_dir():
                    Options.basePath.mkdir(parents=True)
                iconPath = Options.basePath / 'icons'
                if not iconPath.is_dir():
                    iconPath.mkdir()
                templatePath = Options.basePath / 'templates'
                if not templatePath.is_dir():
                    templatePath.mkdir()
                templateExportPath = templatePath / 'exports'
                if not templateExportPath.is_dir():
                    templateExportPath.mkdir()
            except OSError:
                Options.basePath = None
        if Options.basePath:
            self.path = Options.basePath / (fileName + fileNameSuffix)

    def __getitem__(self, name):
        """Return the value of an option when called as options[name].

        Arguments:
            name -- the string key for the option
        """
        return self.get(name).value

    def getDefaultValue(self, name):
        """Return the initially set default value from the given option key.

        Arguments:
            name -- the string key for the option
        """
        return self.get(name).defaultValue

    def changeValue(self, name, value):
        """Set a new value for the given option key.

        Return True if sucessful.
        Arguments:
            name -- the string key for the option
            value -- a value or a string defining the value
        """
        if self.get(name).setValue(value):
            self.modified = True
            return True
        return False

    def resetToDefaults(self, keyList):
        """Reset all options with the given keys to original default values.

        Arguments:
            keyList -- a list of option names to reset
        """
        for key in keyList:
            self.get(key).setValue(self.get(key).defaultValue)
        self.modified = True

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

        Create the file if it isn't found, raise IOError if this fails.
        Only updates existing config items.
        """
        try:
            with self.path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                for key, value in data.items():
                    try:
                        self.get(key).setValue(value)
                    except AttributeError:
                        pass
        except (IOError, ValueError):
            if not self.writeFile():
                raise IOError

    def writeFile(self):
        """Write current options to the file on self.path.

        Returns False on failure.
        """
        try:
            with self.path.open('w', encoding='utf-8') as f:
                data = OrderedDict([(key, obj.storedValue()) for (key, obj) in
                                    self.items()])
                json.dump(data, f, indent=0)
            self.modified = False
        except IOError:
            return False
        return True


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
            if not groupBox or groupBox.title() != option.category:
                groupBox = QGroupBox(option.category)
                rowLayout.addWidget(groupBox)
                QGridLayout(groupBox)
            option.addDialogControl(groupBox)

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
