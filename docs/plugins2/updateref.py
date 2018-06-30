#!/usr/bin/env python3

#****************************************************************************
# updateref.py, a plugin to update empty fields from another file
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#*****************************************************************************

"""updateref - update empty fields from another file.

Use unique IDs to match nodes with fields to update.
"""

import os.path
from PyQt4 import QtCore, QtGui


class UpdateRef:
    """Class for plugin interface.
    """
    fieldName = 'RefNum'
    def __init__(self, interface):
        """Initialize the plugin and its menu.

        Arguments:
            interface -- the treeline plugin interface
        """
        self.interface = interface
        self.interface.setNewWindowCallback(self.addMenu)
        self.action = QtGui.QAction('Update Fields by ID...',
                             self.interface.mainControl(),
                             statusTip='Update empty fields from another file')
        self.action.triggered.connect(self.update)
        self.addMenu()

    def addMenu(self):
        """Add the update fields menu item.
        """
        menu = self.interface.getPulldownMenu(3)
        actionBefore = menu.actions()[4]
        menu.insertAction(actionBefore, self.action)

    def update(self):
        """Update empty fields from another file.
        """
        baseFileName = self.interface.getCurrentFileName()
        baseFilePath = os.path.dirname(baseFileName)
        refFileName = QtGui.QFileDialog.getOpenFileName(QtGui.QApplication.
                                                      activeWindow(),
                                                      'Open Reference File',
                                                      baseFilePath,
                                                      'TreeLine Files (*.trl)')
        if not refFileName:
            return
        refFileName = os.path.normpath(refFileName)
        baseRoot = self.interface.getRootNode()
        self.interface.execMenuAction('WinNewWindow')
        self.interface.openFile(refFileName, False, False)
        if self.interface.getCurrentFileName() != refFileName:
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(),
                                      'TreeLine',
                                      'Error - could not open {0}'.
                                      format(refFileName))
            return
        numChanges = 0
        for baseNode in self.interface.getNodeDescendantList(baseRoot):
            uniqueId = self.interface.getNodeUniqueId(baseNode)
            try:
                refNode = self.interface.getNodeByUniqueId(uniqueId)
            except KeyError:
                continue
            self.interface.openFile(baseFileName, False, False)
            formatName = self.interface.getNodeFormatName(baseNode)
            for fieldName in self.interface.getFormatFieldNames(formatName):
                if not baseNode.data.get(fieldName, ''):
                    refText = refNode.data.get(fieldName, '')
                    if refText:
                        baseNode.data[fieldName] = refText
                        numChanges += 1
            self.interface.openFile(refFileName, False, False)
        self.interface.openFile(baseFileName, False, False)
        if numChanges:
            self.interface.setDocModified()
            self.interface.updateViews()
        QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(),
                                      'TreeLine',
                                      '{0} fields were updated'.
                                      format(numChanges))

def main(interface):
    """Main connection"""
    return UpdateRef(interface)
