#!/usr/bin/env python3

#******************************************************************************
# treelocalcontrol.py, provides a class for the main tree commands
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (QAction, QActionGroup, QMessageBox)
import treestructure
import treemodel
import treewindow
import globalref


class TreeLocalControl(QObject):
    """Class to handle controls local to a model/view combination.

    Provides methods for all local controls and stores a model & windows.
    """
    controlActivated = pyqtSignal(QObject)
    controlClosed = pyqtSignal(QObject)
    def __init__(self, allActions, filePath='', treeStruct=None, parent=None):
        """Initialize the local tree controls.

        Use an imported structure if given or open the file if path is given.
        Always creates a new window.
        Arguments:
            allActions -- a dict containing the upper level actions
            filePath -- the file path or file object to open, if given
            treeStruct -- an imported tree structure file, if given
            parent -- a parent object if given
        """
        super().__init__(parent)
        self.allActions = allActions.copy()
        self.filePath = (filePath.name if hasattr(filePath, 'name') else
                         filePath)
        if treeStruct:
            self.structure = treeStruct
        elif filePath and hasattr(filePath, 'read'):
            self.structure = treestructure.TreeStructure(filePath)
        elif filePath:
            with open(filePath, 'r') as f:
                self.structure = treestructure.TreeStructure(f)
        else:
            self.structure = treestructure.TreeStructure(addDefaults=True)
        self.model = treemodel.TreeModel(self.structure)

        self.modified = False
        self.imported = False
        self.compressed = False
        self.encrypted = False
        self.windowList = []
        self.activeWindow = None
        if not globalref.mainControl.activeControl:
            self.windowNew(0)
        elif False:  # option for open in new window
            self.windowNew()
        else:
            window = globalref.mainControl.activeControl.activeWindow
            window.treeView.setModel(self.model)
            window.treeView.scheduleDelayedItemsLayout() # tmp update command

    def currentTreeView(self):
        """Return the current left-hand tree view.
        """
        return self.activeWindow.treeView

    def setActiveWin(self, window):
        """When a window is activated, stores it and emits a signal.

        Arguments:
            window -- the new active window
        """
        self.activeWindow = window
        self.controlActivated.emit(self)

    def windowNew(self, offset=30):
        """Open a new window for this file.

        Arguments:
            offset -- location offset from previously saved position
        """
        window = treewindow.TreeWindow(self.model, self.allActions)
        window.winActivated.connect(self.setActiveWin)
        # window.winClosing.connect(self.checkWindowClose)
        self.windowList.append(window)
        window.setCaption(self.filePath)
        # window.restoreWindowGeom(offset)
        self.activeWindow = window
        window.show()
