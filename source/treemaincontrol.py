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
import io
import gzip
import zlib
from PyQt5.QtCore import QIODevice, QObject, Qt
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import (QAction, QApplication, QDialog, QFileDialog,
                             QMessageBox, qApp)
import globalref
import treelocalcontrol
import options
import optiondefaults
import recentfiles
import p3
import icondict
import imports
import configdialog
import miscdialogs
import conditional
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

encryptPrefix = b'>>TL+enc'


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
        self.sortDialog = None
        self.numberingDialog = None
        self.findTextDialog = None
        self.findConditionDialog = None
        self.findReplaceDialog = None
        self.filterTextDialog = None
        self.filterConditionDialog = None
        self.passwords = {}
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
                self.openFile(pathObj, True)
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
                        self.openFile(pathlib.Path(path), True)
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
            return
        if checkModified and not (forceNewWindow or
                                  globalref.genOptions['OpenNewWindow'] or
                                  self.activeControl.checkSaveChanges()):
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.createLocalControl(pathObj, None, forceNewWindow)
            self.recentFiles.addItem(pathObj)
            if not (globalref.genOptions['SaveTreeStates'] and
                    self.recentFiles.retrieveTreeState(self.activeControl)):
                self.activeControl.expandRootNodes()
            QApplication.restoreOverrideCursor()
        except IOError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                _('Error - could not read file {0}').
                                format(str(pathObj)))
            self.recentFiles.removeItem(pathObj)
        except (ValueError, KeyError, TypeError):
            fileObj = pathObj.open('rb')
            fileObj, encrypted = self.decryptFile(fileObj)
            if not fileObj:
                if not self.localControls:
                    self.createLocalControl()
                QApplication.restoreOverrideCursor()
                return
            fileObj, compressed = self.decompressFile(fileObj)
            if compressed or encrypted:
                try:
                    textFileObj = io.TextIOWrapper(fileObj, encoding='utf-8')
                    self.createLocalControl(textFileObj, None, forceNewWindow)
                    fileObj.close()
                    textFileObj.close()
                    self.recentFiles.addItem(pathObj)
                    if not (globalref.genOptions['SaveTreeStates'] and
                            self.recentFiles.retrieveTreeState(self.
                                                               activeControl)):
                        self.activeControl.expandRootNodes()
                    self.activeControl.compressed = compressed
                    self.activeControl.encrypted = encrypted
                    QApplication.restoreOverrideCursor()
                    return
                except (ValueError, KeyError, TypeError):
                    pass
            fileObj.close()
            importControl = imports.ImportControl(pathObj)
            structure = importControl.importOldTreeLine()
            if structure:
                self.createLocalControl(pathObj, structure, forceNewWindow)
                self.activeControl.printData.readData(importControl.
                                                      treeLineRootAttrib)
                self.recentFiles.addItem(pathObj)
                self.activeControl.expandRootNodes()
                self.activeControl.imported = True
                QApplication.restoreOverrideCursor()
                return
            QApplication.restoreOverrideCursor()
            if importOnFail:
                importControl = imports.ImportControl(pathObj)
                structure = importControl.interactiveImport(True)
                if structure:
                    self.createLocalControl(pathObj, structure, forceNewWindow)
                    self.activeControl.imported = True
                    return
            else:
                QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                    _('Error - invalid TreeLine file {0}').
                                    format(str(pathObj)))
                self.recentFiles.removeItem(pathObj)
        if not self.localControls:
            self.createLocalControl()

    def decryptFile(self, fileObj):
        """Check for encryption and decrypt the fileObj if needed.

        Return a tuple of the file object and True if it was encrypted.
        Return None for the file object if the user cancels.
        Arguments:
            fileObj -- the file object to check and decrypt
        """
        if fileObj.read(len(encryptPrefix)) != encryptPrefix:
            fileObj.seek(0)
            return (fileObj, False)
        while True:
            pathObj = pathlib.Path(fileObj.name)
            password = self.passwords.get(pathObj, '')
            if not password:
                QApplication.restoreOverrideCursor()
                dialog = miscdialogs.PasswordDialog(False, pathObj.name,
                                                    QApplication.
                                                    activeWindow())
                if dialog.exec_() != QDialog.Accepted:
                    fileObj.close()
                    return (None, True)
                QApplication.setOverrideCursor(Qt.WaitCursor)
                password = dialog.password
                if miscdialogs.PasswordDialog.remember:
                    self.passwords[pathObj] = password
            try:
                text = p3.p3_decrypt(fileObj.read(), password.encode())
                fileIO = io.BytesIO(text)
                fileIO.name = fileObj.name
                fileObj.close()
                return (fileIO, True)
            except p3.CryptError:
                try:
                    del self.passwords[pathObj]
                except KeyError:
                    pass

    def decompressFile(self, fileObj):
        """Check for compression and decompress the fileObj if needed.

        Return a tuple of the file object and True if it was compressed.
        Arguments:
            fileObj -- the file object to check and decompress
        """
        prefix = fileObj.read(2)
        fileObj.seek(0)
        if prefix != b'\037\213':
            return (fileObj, False)
        try:
            newFileObj = gzip.GzipFile(fileobj=fileObj)
        except zlib.error:
            return (fileObj, False)
        newFileObj.name = fileObj.name
        return (newFileObj, True)

    def createLocalControl(self, pathObj=None, treeStruct=None,
                           forceNewWindow=False):
        """Create a new local control object and add it to the list.

        Use an imported structure if given or open the file if path is given.
        Arguments:
            pathObj -- the path object or file object for the control to open
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

        fileSampleAct = QAction(_('Open Sa&mple...'), self,
                                      toolTip=_('Open Sample'),
                                      statusTip=_('Open a sample file'))
        fileSampleAct.triggered.connect(self.fileOpenSample)
        self.allActions['FileOpenSample'] = fileSampleAct

        fileImportAct = QAction(_('&Import...'), self,
                                      statusTip=_('Open a non-TreeLine file'))
        fileImportAct.triggered.connect(self.fileImport)
        self.allActions['FileImport'] = fileImportAct

        fileQuitAct = QAction(_('&Quit'), self,
                              statusTip=_('Exit the application'))
        fileQuitAct.triggered.connect(self.fileQuit)
        self.allActions['FileQuit'] = fileQuitAct

        dataConfigAct = QAction(_('&Configure Data Types...'), self,
                       statusTip=_('Modify data types, fields & output lines'),
                       checkable=True)
        dataConfigAct.triggered.connect(self.dataConfigDialog)
        self.allActions['DataConfigType'] = dataConfigAct

        dataSortAct = QAction(_('Sor&t Nodes...'), self,
                                    statusTip=_('Define node sort operations'),
                                    checkable=True)
        dataSortAct.triggered.connect(self.dataSortDialog)
        self.allActions['DataSortNodes'] = dataSortAct

        dataNumberingAct = QAction(_('Update &Numbering...'), self,
                                   statusTip=_('Update node numbering fields'),
                                   checkable=True)
        dataNumberingAct.triggered.connect(self.dataNumberingDialog)
        self.allActions['DataNumbering'] = dataNumberingAct

        toolsFindTextAct = QAction(_('&Find Text...'), self,
                                statusTip=_('Find text in node titles & data'),
                                checkable=True)
        toolsFindTextAct.triggered.connect(self.toolsFindTextDialog)
        self.allActions['ToolsFindText'] = toolsFindTextAct

        toolsFindConditionAct = QAction(_('&Conditional Find...'), self,
                             statusTip=_('Use field conditions to find nodes'),
                             checkable=True)
        toolsFindConditionAct.triggered.connect(self.toolsFindConditionDialog)
        self.allActions['ToolsFindCondition'] = toolsFindConditionAct

        toolsFindReplaceAct = QAction(_('Find and &Replace...'), self,
                              statusTip=_('Replace text strings in node data'),
                              checkable=True)
        toolsFindReplaceAct.triggered.connect(self.toolsFindReplaceDialog)
        self.allActions['ToolsFindReplace'] = toolsFindReplaceAct

        toolsFilterTextAct = QAction(_('&Text Filter...'), self,
                         statusTip=_('Filter nodes to only show text matches'),
                         checkable=True)
        toolsFilterTextAct.triggered.connect(self.toolsFilterTextDialog)
        self.allActions['ToolsFilterText'] = toolsFilterTextAct

        toolsFilterConditionAct = QAction(_('C&onditional Filter...'),
                           self,
                           statusTip=_('Use field conditions to filter nodes'),
                           checkable=True)
        toolsFilterConditionAct.triggered.connect(self.
                                                  toolsFilterConditionDialog)
        self.allActions['ToolsFilterCondition'] = toolsFilterConditionAct

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
                    self.activeControl.filePathObj = None
                    self.activeControl.updateWindowCaptions()
                    self.activeControl.expandRootNodes()
            else:
                self.createLocalControl()

    def fileOpen(self):
        """Prompt for a filename and open it.
        """
        if (globalref.genOptions['OpenNewWindow'] or
            self.activeControl.checkSaveChanges()):
            filters = ';;'.join((globalref.fileFilters['trlnopen'],
                                 globalref.fileFilters['all']))
            fileName, selFilter = QFileDialog.getOpenFileName(QApplication.
                                                activeWindow(),
                                                _('TreeLine - Open File'),
                                                str(self.defaultPathObj(True)),
                                                filters)
            if fileName:
                self.openFile(pathlib.Path(fileName))

    def fileOpenSample(self):
        """Open a sample file from the doc directories.
        """
        if (globalref.genOptions['OpenNewWindow'] or
            self.activeControl.checkSaveChanges()):
            searchPaths = self.findResourcePaths('samples', samplePath)
            dialog = miscdialogs.TemplateFileDialog(_('Open Sample File'),
                                                    _('&Select Sample'),
                                                    searchPaths, False)
            if dialog.exec_() == QDialog.Accepted:
                self.createLocalControl(dialog.selectedPath())
                name = dialog.selectedName() + '.trln'
                self.activeControl.filePathObj = pathlib.Path(name)
                self.activeControl.updateWindowCaptions()
                self.activeControl.expandRootNodes()
                self.activeControl.imported = True

    def fileImport(self):
        """Prompt for an import type, then a file to import.
        """
        importControl = imports.ImportControl()
        structure = importControl.interactiveImport()
        if structure:
            self.createLocalControl(importControl.pathObj, structure)
            if importControl.treeLineRootAttrib:
                self.activeControl.printData.readData(importControl.
                                                      treeLineRootAttrib)
            self.activeControl.imported = True

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

    def dataSortDialog(self, show):
        """Show or hide the non-modal data sort nodes dialog.

        Arguments:
            show -- true if dialog should be shown, false to hide it
        """
        if show:
            if not self.sortDialog:
                self.sortDialog = miscdialogs.SortDialog()
                dataSortAct = self.allActions['DataSortNodes']
                self.sortDialog.dialogShown.connect(dataSortAct.setChecked)
            self.sortDialog.show()
        else:
            self.sortDialog.close()

    def dataNumberingDialog(self, show):
        """Show or hide the non-modal update node numbering dialog.

        Arguments:
            show -- true if dialog should be shown, false to hide it
        """
        if show:
            if not self.numberingDialog:
                self.numberingDialog = miscdialogs.NumberingDialog()
                dataNumberingAct = self.allActions['DataNumbering']
                self.numberingDialog.dialogShown.connect(dataNumberingAct.
                                                         setChecked)
            self.numberingDialog.show()
            if not self.numberingDialog.checkForNumberingFields():
                self.numberingDialog.close()
        else:
            self.numberingDialog.close()

    def toolsFindTextDialog(self, show):
        """Show or hide the non-modal find text dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.findTextDialog:
                self.findTextDialog = miscdialogs.FindFilterDialog()
                toolsFindTextAct = self.allActions['ToolsFindText']
                self.findTextDialog.dialogShown.connect(toolsFindTextAct.
                                                        setChecked)
            self.findTextDialog.selectAllText()
            self.findTextDialog.show()
        else:
            self.findTextDialog.close()

    def toolsFindConditionDialog(self, show):
        """Show or hide the non-modal conditional find dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.findConditionDialog:
                dialogType = conditional.FindDialogType.findDialog
                self.findConditionDialog = (conditional.
                                            ConditionDialog(dialogType,
                                                        _('Conditional Find')))
                toolsFindConditionAct = self.allActions['ToolsFindCondition']
                (self.findConditionDialog.dialogShown.
                 connect(toolsFindConditionAct.setChecked))
            else:
                self.findConditionDialog.loadTypeNames()
            self.findConditionDialog.show()
        else:
            self.findConditionDialog.close()

    def toolsFindReplaceDialog(self, show):
        """Show or hide the non-modal find and replace text dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.findReplaceDialog:
                self.findReplaceDialog = miscdialogs.FindReplaceDialog()
                toolsFindReplaceAct = self.allActions['ToolsFindReplace']
                self.findReplaceDialog.dialogShown.connect(toolsFindReplaceAct.
                                                           setChecked)
            else:
                self.findReplaceDialog.loadTypeNames()
            self.findReplaceDialog.show()
        else:
            self.findReplaceDialog.close()

    def toolsFilterTextDialog(self, show):
        """Show or hide the non-modal filter text dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.filterTextDialog:
                self.filterTextDialog = miscdialogs.FindFilterDialog(True)
                toolsFilterTextAct = self.allActions['ToolsFilterText']
                self.filterTextDialog.dialogShown.connect(toolsFilterTextAct.
                                                          setChecked)
            self.filterTextDialog.selectAllText()
            self.filterTextDialog.show()
        else:
            self.filterTextDialog.close()

    def toolsFilterConditionDialog(self, show):
        """Show or hide the non-modal conditional filter dialog.

        Arguments:
            show -- true if dialog should be shown
        """
        if show:
            if not self.filterConditionDialog:
                dialogType = conditional.FindDialogType.filterDialog
                self.filterConditionDialog = (conditional.
                                              ConditionDialog(dialogType,
                                                      _('Conditional Filter')))
                toolsFilterConditionAct = (self.
                                        allActions[_('ToolsFilterCondition')])
                (self.filterConditionDialog.dialogShown.
                 connect(toolsFilterConditionAct.setChecked))
            else:
                self.filterConditionDialog.loadTypeNames()
            self.filterConditionDialog.show()
        else:
            self.filterConditionDialog.close()

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
