#!/usr/bin/env python3

#******************************************************************************
# colorset.py, provides storage/retrieval and dialogs for GUI colors
#
# TreeLine, an information storage program
# Copyright (C) 2025, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import enum
from collections import OrderedDict
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QObject
from PyQt6.QtGui import QColor, QFontMetrics, QPalette, QPixmap
from PyQt6.QtWidgets import (QApplication, QColorDialog, QComboBox, QDialog,
                             QFrame, QGroupBox, QHBoxLayout, QLabel,
                             QGridLayout, QPushButton, QVBoxLayout)
import globalref

roles = OrderedDict([('Window', _('Dialog background color')),
                     ('WindowText', _('Dialog text color')),
                     ('Base', _('Text widget background color')),
                     ('Text', _('Text widget foreground color')),
                     ('Highlight', _('Selected item background color')),
                     ('HighlightedText', _('Selected item text color')),
                     ('Link', _('Link text color')),
                     ('ToolTipBase', _('Tool tip background color')),
                     ('ToolTipText', _('Tool tip foreground color')),
                     ('Button', _('Button background color')),
                     ('ButtonText', _('Button text color')),
                     ('Text-Disabled', _('Disabled text foreground color')),
                     ('ButtonText-Disabled', _('Disabled button text color'))])

ThemeSetting = enum.IntEnum('ThemeSetting', 'system dark custom')

darkColors = {'Window': '#353535', 'WindowText': '#ffffff',
              'Base': '#191919', 'Text': '#ffffff',
              'Highlight': '#2a82da', 'HighlightedText': '#000000',
              'Link': '#2a82da', 'ToolTipBase': '#000080',
              'ToolTipText': '#c0c0c0', 'Button': '#353535',
              'ButtonText': '#ffffff', 'Text-Disabled': '#808080',
              'ButtonText-Disabled': '#808080'}


class ColorSet:
    """Stores color settings and provides dialogs for user changes.
    """
    def __init__(self):
        """Initialize colors settings from the system or from options.
        """
        self.sysPalette = QApplication.palette()
        self.colors = [Color(roleKey) for roleKey in roles.keys()]
        self.theme = ThemeSetting[globalref.miscOptions['ColorTheme']]
        for color in self.colors:
            color.colorChanged.connect(self.setCustomTheme)
            color.setFromPalette(self.sysPalette)
            if self.theme == ThemeSetting.dark:
                color.setFromTheme(darkColors)
            elif self.theme == ThemeSetting.custom:
                color.setFromOption()

    def setAppColors(self):
        """Set application to current colors.
        """
        newPalette = QApplication.palette()
        for color in self.colors:
            color.updatePalette(newPalette)
        QApplication.setPalette(newPalette)


    def showDialog(self, parent):
        """Show a dialog for user color changes.

        Return True if changes were made.
        Arguments:
            parent -- the parent widget for the dialog
        """
        dialog = QDialog(parent)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint |
                              Qt.WindowType.WindowSystemMenuHint)
        dialog.setWindowTitle(_('Color Settings'))
        topLayout = QVBoxLayout(dialog)
        dialog.setLayout(topLayout)
        themeBox = QGroupBox(_('Color Theme'), dialog)
        topLayout.addWidget(themeBox)
        themeLayout = QVBoxLayout(themeBox)
        self.themeControl = QComboBox(dialog)
        self.themeControl.addItem(_('Default system theme'),
                                  ThemeSetting.system)
        self.themeControl.addItem(_('Dark theme'), ThemeSetting.dark)
        self.themeControl.addItem(_('Custom theme'), ThemeSetting.custom)
        self.themeControl.setCurrentIndex(self.themeControl.
                                          findData(self.theme))
        self.themeControl.currentIndexChanged.connect(self.updateThemeSetting)
        themeLayout.addWidget(self.themeControl)
        self.groupBox = QGroupBox(dialog)
        self.setBoxTitle()
        topLayout.addWidget(self.groupBox)
        gridLayout = QGridLayout(self.groupBox)
        row = 0
        for color in self.colors:
            gridLayout.addWidget(color.getLabel(), row, 0)
            gridLayout.addWidget(color.getSwatch(), row, 1)
            row += 1
        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch(0)
        okButton = QPushButton(_('&OK'), dialog)
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(dialog.accept)
        cancelButton = QPushButton(_('&Cancel'), dialog)
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.theme = ThemeSetting(self.themeControl.currentData())
            globalref.miscOptions.changeValue('ColorTheme', self.theme.name)
            if self.theme == ThemeSetting.system:
                QApplication.setPalette(self.sysPalette)
            else:   # dark theme or custom
                if self.theme == ThemeSetting.custom:
                    for color in self.colors:
                        color.updateOption()
                self.setAppColors()
            globalref.miscOptions.writeFile()
        else:
            for color in self.colors:
                color.setFromPalette(self.sysPalette)
                if self.theme == ThemeSetting.dark:
                    color.setFromTheme(darkColors)
                elif self.theme == ThemeSetting.custom:
                    color.setFromOption()

    def setBoxTitle(self):
        """Set title of group box to standard or custom.
        """
        if self.themeControl.currentData() == ThemeSetting.custom:
            title = _('Custom Colors')
        else:
            title = _('Theme Colors')
        self.groupBox.setTitle(title)

    def updateThemeSetting(self):
        """Update the colors based on a theme control change.
        """
        if self.themeControl.currentData() == ThemeSetting.system:
            for color in self.colors:
                color.setFromPalette(self.sysPalette)
                color.changeSwatchColor()
        elif self.themeControl.currentData() == ThemeSetting.dark:
            for color in self.colors:
                color.setFromTheme(darkColors)
                color.changeSwatchColor()
        else:
            for color in self.colors:
                color.setFromOption()
                color.changeSwatchColor()
        self.setBoxTitle()

    def setCustomTheme(self):
        """Set to custom theme setting after user color change.
        """
        if self.themeControl.currentData != ThemeSetting.custom:
            self.themeControl.blockSignals(True)
            self.themeControl.setCurrentIndex(2)
            self.themeControl.blockSignals(False)
            self.setBoxTitle()


class Color(QObject):
    """Stores a single color setting for a role.
    """
    colorChanged = pyqtSignal()
    def __init__(self, roleKey, parent=None):
        """Initialize a Color.

        Arguments:
            roleKey -- the text name of the color role
            parent -- a parent object if given
        """
        super().__init__(parent)
        self.roleKey = roleKey
        if '-' in roleKey:
            roleStr, groupStr = roleKey.split('-')
            self.group = eval('QPalette.ColorGroup.' + groupStr)
        else:
            roleStr = roleKey
            self.group = None
        self.role = eval('QPalette.ColorRole.' + roleStr)
        self.currentColor = None
        self.swatch = None

    def setFromPalette(self, palette):
        """Set the color based on the given palette.

        Arguments:
            palette -- the palette that defines the color
        """
        if self.group:
            self.currentColor = palette.color(self.group, self.role)
        else:
            self.currentColor = palette.color(self.role)

    def setFromOption(self):
        """Set color based on the option setting.
        """
        colorStr = globalref.miscOptions[self.roleKey + 'Color']
        color = QColor(colorStr)
        if color.isValid():
            self.currentColor = color

    def setFromTheme(self, theme):
        """Set color based on the given theme dictionary.

        Arguments:
            theme -- a theme dictionary that defines the color
        """
        self.currentColor = QColor(theme[self.roleKey])

    def updateOption(self):
        """Set the option to the current color.
        """
        if self.currentColor:
            globalref.miscOptions.changeValue(self.roleKey + 'Color',
                                              self.currentColor.name())

    def updatePalette(self, palette):
        """Set the role in the given palette to the current color.

        Arguments:
            palette -- the palette that gets set with the color
        """
        if self.group:
            palette.setColor(self.group, self.role, self.currentColor)
        else:
            palette.setColor(self.role, self.currentColor)

    def getLabel(self):
        """Return a label for this role in a dialog.
        """
        return QLabel(roles[self.roleKey])

    def getSwatch(self):
        """Return a label color swatch with the current color.
        """
        self.swatch = QLabel()
        self.changeSwatchColor()
        self.swatch.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
        self.swatch.setLineWidth(3)
        self.swatch.installEventFilter(self)
        return self.swatch

    def changeSwatchColor(self):
        """Set swatch to currentColor.
        """
        height = QFontMetrics(self.swatch.font()).height()
        pixmap = QPixmap(3 * height, height)
        pixmap.fill(self.currentColor)
        self.swatch.setPixmap(pixmap)

    def eventFilter(self, obj, event):
        """Handle mouse clicks on swatches.

        Arguments:
            obj -- the object to handle events for
            event -- the specific event
        """
        if (obj == self.swatch and
            event.type() == QEvent.Type.MouseButtonRelease):
            color = QColorDialog.getColor(self.currentColor,
                                          QApplication.activeWindow(),
                                          _('Select {0} color').
                                          format(self.roleKey))
            if color.isValid() and color != self.currentColor:
                self.currentColor = color
                self.changeSwatchColor()
                self.colorChanged.emit()
            return True
        return False
