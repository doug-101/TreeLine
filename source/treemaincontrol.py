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
import ast
from PyQt5.QtCore import QIODevice, QObject, Qt
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import (QAction, QApplication, QDialog, QFileDialog,
                             QMessageBox, qApp)
import globalref
import treelocalcontrol
import options
import optiondefaults
import recentfiles
import icondict
import configdialog
import miscdialogs
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
        self.configDialog = None
        self.findTextDialog = None
        globalref.mainControl = self
        self.allActions = {}
        try:
            # check for existing TreeLine session
            socket = QLocalSocket()
            socket.connectToServer('treeline3-session',
                                   QIODevice.WriteOnly)
            # if found, send files to open and exit TreeLine
            if socket.waitForConnected(1000):
                socket.write(bytes(repr([str(path) for path in pathObjects]),
                                   'utf-8'))
                if socket.waitForBytesWritten(1000):
                    socket.close()
                    sys.exit(0)
            # start local server to listen for attempt to start new session
            self.serverSocket = QLocalServer()
            self.serverSocket.listen('treeline3-session')
            self.serverSocket.newConnection.connect(self.getSocket)
        except AttributeError:
            print(_('Warning:  Could not create local socket'))
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
        self.recentFiles = recentfiles.RecentFileList()
        if globalref.genOptions['AutoFileOpen'] and not pathObjects:
            recentPath = self.recentFiles.firstPath()
            if recentPath:
                pathObjects = [recentPath]
        self.setupActions()
        qApp.focusChanged.connect(self.updateActionsAvail)
        if pathObjects:
            for pathObj in pathObjects:
                self.openFile(pathObj.resolve(), True)
        else:
            self.createLocalControl()

    def getSocket(self):
        """Open a socket from an attempt to open a second Treeline instance.

        Opens the file (or raise and focus if open) in this instance.
        """
        socket = self.serverSocket.nextPendingConnection()
        if socket and socket.waitForReadyRead(1000):
            data = str(socket.readAll(), 'utf-8')
            try:
                paths = ast.literal_eval(data)
                if paths:
                    for path in paths:
                        self.openFile(pathlib.Path(path).resolve(), True)
                else:
                    self.activeControl.activeWindow.activateAndRaise()
            except(SyntaxError, ValueError, TypeError):
                pass

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
            pathObj = self.recentFiles.firstDir()
            if not pathObj:
                pathObj = pathlib.Path.home()
        if dirOnly:
            pathObj = pathObj.parent
        return pathObj

    def openFile(self, pathObj, forceNewWindow=False, checkModified=False,
                 importOnFail=True):
        """Open the file given by path if not already open.

        If already open in a different window, focus and raise the window.
        Arguments:
            pathObj -- the path object to read
            forceNewWindow -- if True, use a new window regardless of option
            checkModified -- if True & not new win, prompt if file modified
            importOnFail -- if True, prompts for import on non-TreeLine files
        """
        match = [control for control in self.localControls if
                 pathObj == control.filePathObj]
        if match and self.activeControl not in match:
            control = match[0]
            control.activeWindow.activateAndRaise()
            self.updateLocalControlRef(control)
        elif (not checkModified or forceNewWindow or
              globalref.genOptions['OpenNewWindow'] or
              self.activeControl.checkSaveChanges()):
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.createLocalControl(pathObj, None, forceNewWindow)
                self.recentFiles.addItem(pathObj)
                if globalref.genOptions['SaveTreeStates']:
                    self.recentFiles.retrieveTreeState(self.activeControl)
                QApplication.restoreOverrideCursor()
            except IOError:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                    _('Error - could not read file {0}').
                                    format(str(pathObj)))
                self.recentFiles.removeItem(pathObj)
            except (ValueError, KeyError, TypeError):
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                    _('Error - invalid TreeLine file {0}').
                                    format(str(pathObj)))
                self.recentFiles.removeItem(pathObj)
            if not self.localControls:
                self.createLocalControl()

    def createLocalControl(self, pathObj=None, treeStruct=None,
                           forceNewWindow=False):
        """Create a new local control object and add it to the list.

        Use an imported structure if given or open the file if path is given.
        Arguments:
            pathObj -- the path object for the control to open
            treeStruct -- the imported structure to use
            forceNewWindow -- if True, use a new window regardless of option
        """
        localControl = treelocalcontrol.TreeLocalControl(self.allActions,
                                                         pathObj, treeStruct,
                                                         forceNewWindow)
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
            if self.configDialog and self.configDialog.isVisible():
                self.configDialog.setRefs(self.activeControl)

    def removeLocalControlRef(self, localControl):
        """Remove ref to local control based on a closing signal.

        Also do application exit clean ups if last control closing.
        Arguments:
            localControl -- the local control that is closing
        """
        self.localControls.remove(localControl)
        if globalref.genOptions['SaveTreeStates']:
            self.recentFiles.saveTreeState(localControl)
        if not self.localControls:
            if globalref.genOptions['SaveWindowGeom']:
                localControl.windowList[0].saveWindowGeom()
            else:
                localControl.windowList[0].resetWindowGeom()
            self.recentFiles.writeItems()
            localControl.windowList[0].saveToolbarPosition()
            globalref.histOptions.writeFile()

    def currentStatusBar(self):
        """Return the status bar from the current main window.
        """
        return self.activeControl.activeWindow.statusBar()

    def windowActions(self):
        """Return a list of window menu actions from each local control.
        """
        actions = []
        for control in self.localControls:
            actions.extend(control.windowActions(len(actions) + 1,
                                                control == self.activeControl))
        return actions

    def updateActionsAvail(self, oldWidget, newWidget):
        """Update command availability based on focus changes.

        Arguments:
            oldWidget -- the previously focused widget
            newWidget -- the newly focused widget
        """
        self.allActions['FormatSelectAll'].setEnabled(hasattr(newWidget,
                                                              'selectAll') and
                                                    not hasattr(newWidget,
                                                               'editTriggers'))

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

        dataConfigAct = QAction(_('&Configure Data Types...'), self,
                       statusTip=_('Modify data types, fields & output lines'),
                       checkable=True)
        dataConfigAct.triggered.connect(self.dataConfigDialog)
        self.allActions['DataConfigType'] = dataConfigAct

        toolsFindTextAct = QAction(_('&Find Text...'), self,
                                statusTip=_('Find text in node titles & data'),
                                checkable=True)
        toolsFindTextAct.triggered.connect(self.toolsFindTextDialog)
        self.allActions['ToolsFindText'] = toolsFindTextAct

        toolsGenOptionsAct = QAction(_('&General Options...'), self,
                             statusTip=_('Set user preferences for all files'))
        toolsGenOptionsAct.triggered.connect(self.toolsGenOptions)
        self.allActions['ToolsGenOptions'] = toolsGenOptionsAct

        formatSelectAllAct =  QAction(_('&Select All'), self,
                                   statusTip=_('Select all text in an editor'))
        formatSelectAllAct.setEnabled(False)
        formatSelectAllAct.triggered.connect(self.formatSelectAll)
        self.allActions['FormatSelectAll'] = formatSelectAllAct

        helpAboutAct = QAction(_('&About TreeLine...'), self,
                        statusTip=_('Display version info about this program'))
        helpAboutAct.triggered.connect(self.helpAbout)
        self.allActions['HelpAbout'] = helpAboutAct

        for name, action in self.allActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions[name]
            if not key.isEmpty():
                action.setShortcut(key)

    def fileNew(self):
        """Start a new blank file.
        """
        if (globalref.genOptions['OpenNewWindow'] or
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
        if (globalref.genOptions['OpenNewWindow'] or
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

    def dataConfigDialog(self, show):
        """Show or hide the non-modal data config dialog.

        Arguments:
            show -- true if dialog should be shown, false to hide it
        """
        if show:
            if not self.configDialog:
                self.configDialog = configdialog.ConfigDialog()
                dataConfigAct = self.allActions['DataConfigType']
                self.configDialog.dialogShown.connect(dataConfigAct.setChecked)
            self.configDialog.setRefs(self.activeControl, True)
            self.configDialog.show()
        else:
            self.configDialog.close()

    def toolsFindTextDialog(self, show):
        """Show or hide the non-modal find text dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.findTextDialog:
                self.findTextDialog = (miscdialogs.FindFilterDialog())
                toolsFindTextAct = self.allActions['ToolsFindText']
                self.findTextDialog.dialogShown.connect(toolsFindTextAct.
                                                        setChecked)
            self.findTextDialog.selectAllText()
            self.findTextDialog.show()
        else:
            self.findTextDialog.close()

    def toolsGenOptions(self):
        """Set general user preferences for all files.
        """
        dialog = options.OptionDialog(globalref.genOptions,
                                      QApplication.activeWindow())
        dialog.setWindowTitle(_('General Options'))
        if (dialog.exec_() == QDialog.Accepted and
            globalref.genOptions.modified):
            globalref.genOptions.writeFile()
            self.recentFiles.updateNumEntries()
            for control in self.localControls:
                for window in control.windowList:
                    window.treeView.updateTreeGenOptions()
                control.updateAll(False)

    def formatSelectAll(self):
        """Select all text in any currently focused editor.
        """
        try:
            QApplication.focusWidget().selectAll()
        except AttributeError:
            pass

    def helpAbout(self):
        """ Display version info about this program.
        """
        QMessageBox.about(QApplication.activeWindow(), 'TreeLine',
                          _('TreeLine, Version {0}\nby {1}').
                          format(__version__, __author__))
