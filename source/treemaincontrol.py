#!/usr/bin/env python3

#******************************************************************************
# treemaincontrol.py, provides a class for global tree commands
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import sys
import pathlib
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import (QAction, QApplication, QFileDialog, QMessageBox)
import globalref
import treelocalcontrol
import options
import optiondefaults
import icondict
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
    def __init__(self, pathObjects, parent=None):
        """Initialize the main tree controls

        Arguments:
            pathObjects -- a list of file objects to open
            parent -- the parent QObject if given
        """
        super().__init__(parent)
        self.localControls = []
        self.activeControl = None
        globalref.mainControl = self
        self.allActions = {}
        mainVersion = '.'.join(__version__.split('.')[:2])
        globalref.genOptions = options.Options('general', 'TreeLine',
                                               mainVersion, 'bellz')
        optiondefaults.setGenOptionDefaults(globalref.genOptions)
        globalref.miscOptions  = options.Options('misc')
        optiondefaults.setMiscOptionDefaults(globalref.miscOptions)
        globalref.histOptions = options.Options('history')
        optiondefaults.setHistOptionDefaults(globalref.histOptions)
        globalref.toolbarOptions = options.Options('toolbar')
        optiondefaults.setToolbarOptionDefaults(globalref.toolbarOptions)
        globalref.keyboardOptions = options.Options('keyboard')
        optiondefaults.setKeyboardOptionDefaults(globalref.keyboardOptions)
        try:
            globalref.genOptions.readFile()
            globalref.miscOptions.readFile()
            globalref.histOptions.readFile()
            globalref.toolbarOptions.readFile()
            globalref.keyboardOptions.readFile()
        except IOError:
            QMessageBox.warning(None, 'TreeLine',
                                _('Error - could not write config file to {}').
                                format(options.Options.basePath))
        iconPathList = self.findResourcePaths('icons', iconPath)
        globalref.toolIcons = icondict.IconDict([path / 'toolbar' for path
                                                 in iconPathList],
                                                ['', '32x32', '16x16'])
        globalref.toolIcons.loadAllIcons()
        windowIcon = globalref.toolIcons.getIcon('treelogo')
        if windowIcon:
            QApplication.setWindowIcon(windowIcon)
        globalref.treeIcons = icondict.IconDict(iconPathList, ['', 'tree'])
        icon = globalref.treeIcons.getIcon('default')
        self.setupActions()
        if pathObjects:
            for pathObj in pathObjects:
                self.openFile(pathObj.resolve())
        else:
            self.createLocalControl()

    def findResourcePaths(self, resourceName, preferredPath=''):
        """Return list of potential non-empty pathlib objects for the resource.

        List includes preferred, module and user option paths.
        Arguments:
            resourceName -- the typical name of the resource directory
            preferredPath -- add this as the second path if given
        """
        modPath = pathlib.Path(sys.path[0]).resolve()
        basePath = pathlib.Path(options.Options.basePath)
        pathList = [basePath / resourceName, modPath / '..' / resourceName,
                    modPath / resourceName]
        if preferredPath:
            pathList.insert(1, pathlib.Path(preferredPath))
        return [path.resolve() for path in pathList if path.is_dir() and
                list(path.iterdir())]

    def defaultPathObj(self, dirOnly=False):
        """Return a reasonable default file path object.

        Used for open, save-as, import and export.
        Arguments:
            dirOnly -- if True, do not include basename of file
        """
        pathObj = None
        if  self.activeControl:
            pathObj = self.activeControl.filePathObj
        if not pathObj:
            # pathObj = self.recentFiles.firstDir()
            # if not pathObj:
            pathObj = pathlib.Path.home()
        if dirOnly:
            pathObj = pathObj.parent
        return pathObj

    def openFile(self, pathObj, checkModified=False, importOnFail=True):
        """Open the file given by path if not already open.

        If already open in a different window, focus and raise the window.
        Arguments:
            pathObj -- the name of the file path to read
            checkModified -- if True, prompt user about current modified file
            importOnFail -- if True, prompts for import on non-TreeLine files
        """
        match = [control for control in self.localControls if
                 pathObj == control.filePathObj]
        if match and self.activeControl not in match:
            control = match[0]
            control.activeWindow.activateAndRaise()
            self.updateLocalControlRef(control)
        else:
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.createLocalControl(pathObj)
                QApplication.restoreOverrideCursor()
            except IOError:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                    _('Error - could not read file {0}').
                                    format(str(pathObj)))
            except (ValueError, KeyError, TypeError):
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                    _('Error - invalid TreeLine file {0}').
                                    format(str(pathObj)))
            if not self.localControls:
                self.createLocalControl()

    def createLocalControl(self, pathObj=None, treeStruct=None):
        """Create a new local control object and add it to the list.

        Use an imported structure if given or open the file if path is given.
        Arguments:
            pathObj -- the path object for the control to open
            treeStruct -- the imported structure to use
        """
        localControl = treelocalcontrol.TreeLocalControl(self.allActions,
                                                         pathObj, treeStruct)
        localControl.controlActivated.connect(self.updateLocalControlRef)
        localControl.controlClosed.connect(self.removeLocalControlRef)
        self.localControls.append(localControl)
        self.updateLocalControlRef(localControl)
        localControl.updateRightViews()

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

    def currentStatusBar(self):
        """Return the status bar from the current main window.
        """
        return self.activeControl.activeWindow.statusBar()

    def setupActions(self):
        """Add the actions for contols at the global level.
        """
        fileNewAct = QAction(_('&New...'), self, toolTip=_('New File'),
                             statusTip=_('Start a new file'))
        fileNewAct.triggered.connect(self.fileNew)
        self.allActions['FileNew'] = fileNewAct

        fileOpenAct = QAction(_('&Open...'), self, toolTip=_('Open File'),
                              statusTip=_('Open a file from disk'))
        fileOpenAct.triggered.connect(self.fileOpen)
        self.allActions['FileOpen'] = fileOpenAct

        fileQuitAct = QAction(_('&Quit'), self,
                              statusTip=_('Exit the application'))
        fileQuitAct.triggered.connect(self.fileQuit)
        self.allActions['FileQuit'] = fileQuitAct

        for name, action in self.allActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions.getValue(name)
            if not key.isEmpty():
                action.setShortcut(key)

    def fileNew(self):
        """Start a new blank file.
        """
        if (globalref.genOptions.getValue('OpenNewWindow') or
            self.activeControl.checkSaveChanges()):
            searchPaths = self.findResourcePaths('templates', templatePath)
            if searchPaths:
                dialog = miscdialogs.TemplateFileDialog(_('New File'),
                                                        _('&Select Template'),
                                                        searchPaths)
                if dialog.exec_() == QDialog.Accepted:
                    self.createLocalControl(dialog.selectedPath())
                    self.activeControl.filePath = ''
                    self.activeControl.updateWindowCaptions()
            else:
                self.createLocalControl()

    def fileOpen(self):
        """Prompt for a filename and open it.
        """
        if (globalref.genOptions.getValue('OpenNewWindow') or
            self.activeControl.checkSaveChanges()):
            filters = ';;'.join((globalref.fileFilters['trl'],
                                 globalref.fileFilters['trlgz'],
                                 globalref.fileFilters['trlenc'],
                                 globalref.fileFilters['all']))
            fileName, selFilter = QFileDialog.getOpenFileName(QApplication.
                                                activeWindow(),
                                                _('TreeLine - Open File'),
                                                str(self.defaultPathObj(True)),
                                                filters)
            if fileName:
                self.openFile(pathlib.Path(fileName))

    def fileQuit(self):
        """Close all windows to exit the applications.
        """
        for control in self.localControls[:]:
            control.closeWindows()
