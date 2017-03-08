#!/usr/bin/env python3

#******************************************************************************
# treemaincontrol.py, provides a class for global tree commands
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import pathlib
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import (QAction, QApplication, QMessageBox)
import globalref
import treelocalcontrol
try:
    from __main__ import __version__, __author__
except ImportError:
    __version__ = ''
    __author__ = ''
try:
    from __main__ import docPath, iconPath, templatePath, samplePath
except ImportError:
    docPath = None
    iconPath = None
    templatePath = None
    samplePath = None


class TreeMainControl(QObject):
    """Class to handle all global controls.

    Provides methods for all controls and stores local control objects.
    """
    def __init__(self, filePaths, parent=None):
        """Initialize the main tree controls

        Arguments:
            filePaths -- a list of files to open
            parent -- the parent QObject if given
        """
        super().__init__(parent)
        self.localControls = []
        self.activeControl = None
        globalref.mainControl = self
        self.allActions = {}
        if filePaths:
            for path in filePaths:
                self.openFile(path)
        else:
            self.createLocalControl()

    def openFile(self, filePath, checkModified=False, importOnFail=True):
        """Open the file given by path if not already open.

        If already open in a different window, focus and raise the window.
        Arguments:
            filePath -- the name of the file path to read
            checkModified -- if True, prompt user about current modified file
            importOnFail -- if True, prompts for import on non-TreeLine files
        """
        path = pathlib.Path(filePath).resolve()
        match = [control for control in self.localControls if
                 path == pathlib.Path(control.filePath)]
        if match and self.activeControl not in match:
            control = match[0]
            control.activeWindow.activateAndRaise()
            self.updateLocalControlRef(control)
        else:
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.createLocalControl(str(path))
                QApplication.restoreOverrideCursor()
            except IOError:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                    _('Error - could not read file {0}').
                                    format(str(path)))
            if not self.localControls:
                self.createLocalControl()

    def createLocalControl(self, path='', treeStruct=None):
        """Create a new local control object and add it to the list.

        Use an imported structure if given or open the file if path is given.
        Arguments:
            path -- the path for the control to open
            treeStruct -- the imported structure to use
        """
        localControl = treelocalcontrol.TreeLocalControl(self.allActions, path,
                                                         treeStruct)
        localControl.controlActivated.connect(self.updateLocalControlRef)
        localControl.controlClosed.connect(self.removeLocalControlRef)
        self.localControls.append(localControl)
        self.updateLocalControlRef(localControl)

    def updateLocalControlRef(self, localControl):
        """Set the given local control as active.

        Called by signal from a window becoming active.
        Also updates non-modal dialogs.
        Arguments:
            localControl -- the new active local control
        """
        if localControl != self.activeControl:
            self.activeControl = localControl

    def removeLocalControlRef(self, localControl):
        """Remove ref to local control based on a closing signal.

        Also do application exit clean ups if last control closing.
        Arguments:
            localControl -- the local control that is closing
        """
        self.localControls.remove(localControl)

    def currentTreeView(self):
        """Return the current left-hand tree view.
        """
        return self.activeControl.currentTreeView()

    def currentStatusBar(self):
        """Return the status bar from the current main window.
        """
        return self.activeControl.activeWindow.statusBar()
