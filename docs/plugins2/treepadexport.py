#!/usr/bin/env python3

#******************************************************************************
# treepadexport.py, a plugin to export TreeLine files to Treepad format
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

"""exportTreepad - export TreeLine files to Treepad format
"""

import os.path
import locale
from PyQt4 import QtCore, QtGui


class TreepadExport:
    """Class for exporting to Treepad files.
    """
    def __init__(self, interface):
        """Initialize the plugin and its menu.

        Arguments:
            interface -- the treeline plugin interface
        """
        self.interface = interface
        self.interface.setNewWindowCallback(self.addMenu)
        self.action = QtGui.QAction('E&xport to Treepad...',
                        self.interface.mainControl(),
                        statusTip='Exports entire file to Treepad text format')
        self.action.triggered.connect(self.exportToTreepad)
        self.addMenu()

    def addMenu(self):
        """Add the export menu item.
        """
        menu = self.interface.getPulldownMenu(0)
        actionBefore = menu.actions()[8]
        menu.insertAction(actionBefore, self.action)

    def exportToTreepad(self):
        """Prompt the user for a file name and perform the export.
        """
        defaultPath = ''
        rootFileName = os.path.splitext(self.interface.getCurrentFileName())[0]
        if os.path.basename(rootFileName):
            defaultPath = '{0}.{1}'.format(rootFileName, 'hjt')
        filters = 'Treepad Files (*.hjt);;All Files (*)'
        filePath = QtGui.QFileDialog.getSaveFileName(self.interface.
                                                     getActiveWindow(),
                                                     'TreeLine', defaultPath,
                                                     filters)
        if filePath:
            textList = self.exportNode(self.interface.getRootNode())
            textList.insert(0, '<hj-Treepad version 0.9>')
            encoding = locale.getpreferredencoding()
            try:
                with open(filePath, 'w', encoding=encoding) as f:
                    f.writelines([(line + '\n') for line in textList])
            except IOError:
                QtGui.QMessageBox.warning(self.interface.getActiveWindow(),
                                          'TreeLine',
                                          'Error - could not write to {}'
                                          .format(filePath))

    def exportNode(self, node, level=0):
        """Return a text list with output for this node and its descendents.

        Arguments:
            node -- the parent node to export
            level -- the level number
        """
        title = node.title()
        textList = ['<node>', title, repr(level)]
        output = node.formatOutput(True)
        if output and output[0] == title:
            del output[0]      # remove first line if same as title
        textList.extend(output)
        if (output and
            self.interface.getFormatSpaceBetween(self.interface.
                                                 getNodeFormatName(node))):
            textList.append('')
        textList.append('<end node> 5P9i0s8y19Z')
        for child in node.childList:
            textList.extend(self.exportNode(child, level + 1))
        return textList


def main(interface):
    """Main interface connection.
    """
    return TreepadExport(interface)
