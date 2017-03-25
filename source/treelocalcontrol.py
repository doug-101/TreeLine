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

import pathlib
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QFileDialog,
                             QMessageBox)
import treestructure
import treemodel
import treewindow
import undo
import globalref


class TreeLocalControl(QObject):
    """Class to handle controls local to a model/view combination.

    Provides methods for all local controls and stores a model & windows.
    """
    controlActivated = pyqtSignal(QObject)
    controlClosed = pyqtSignal(QObject)
    def __init__(self, allActions, fileObj=None, treeStruct=None, parent=None):
        """Initialize the local tree controls.

        Use an imported structure if given or open the file if path is given.
        Always creates a new window.
        Arguments:
            allActions -- a dict containing the upper level actions
            fileObj -- the path object or file object to open, if given
            treeStruct -- an imported tree structure file, if given
            parent -- a parent object if given
        """
        super().__init__(parent)
        self.allActions = allActions.copy()
        self.setupActions()
        self.filePathObj = (pathlib.Path(fileObj.name) if
                            hasattr(fileObj, 'read') else fileObj)
        if treeStruct:
            self.structure = treeStruct
        elif fileObj and hasattr(fileObj, 'read'):
            self.structure = treestructure.TreeStructure(fileObj)
        elif fileObj:
            with fileObj.open('r', encoding='utf-8') as f:
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
        self.structure.undoList = undo.UndoRedoList(self.
                                                    allActions['EditUndo'],
                                                    self)
        self.structure.redoList = undo.UndoRedoList(self.
                                                    allActions['EditRedo'],
                                                    self)
        self.structure.undoList.altListRef = self.structure.redoList
        self.structure.redoList.altListRef = self.structure.undoList
        if not globalref.mainControl.activeControl:
            self.windowNew(0)
        elif globalref.genOptions.getValue('OpenNewWindow'):
            self.windowNew()
        else:
            oldControl = globalref.mainControl.activeControl
            window = oldControl.activeWindow
            oldControl.controlClosed.emit(oldControl)
            window.resetTreeModel(self.model)
            self.setWindowSignals(window, True)
            self.windowList.append(window)
            window.setCaption(self.filePathObj)
            self.activeWindow = window

    def setWindowSignals(self, window, removeOld=False):
        """Setup signals between the window and this controller.

        Arguments:
            window -- the window to link
            removeOld -- if True, remove old signals
        """
        if removeOld:
            window.selectChanged.disconnect()
            window.nodeModified.disconnect()
            window.treeModified.disconnect()
            window.winActivated.disconnect()
            window.winClosing.disconnect()
        window.selectChanged.connect(self.updateCommandsAvail)
        window.nodeModified.connect(self.updateTreeNode)
        window.treeModified.connect(self.updateTree)
        window.winActivated.connect(self.setActiveWin)
        window.winClosing.connect(self.checkWindowClose)

    def updateTreeNode(self, node, setModified=True):
        """Update the full tree in all windows.

        Also update right views in secondary windows.
        Arguments:
            node -- the node to be updated
            setModified -- if True, set the modified flag for this file
        """
        for window in self.windowList:
            window.updateTreeNode(node)
        if setModified:
            self.setModified()

    def updateTree(self, setModified=True):
        """Update the full tree in all windows.

        Also update right views in secondary windows.
        Arguments:
            setModified -- if True, set the modified flag for this file
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        for window in self.windowList:
            window.updateTree()
            if window != self.activeWindow:
                window.updateRightViews()
        if setModified:
            self.setModified()
        QApplication.restoreOverrideCursor()

    def updateRightViews(self, setModified=False):
        """Update the right-hand views in all windows.

        Arguments:
            setModified -- if True, set the modified flag for this file
        """
        for window in self.windowList:
            window.updateRightViews()
        if setModified:
            self.setModified()

    def updateAll(self, setModified=True):
        """Update the full tree and right-hand views in all windows.

        Arguments:
            setModified -- if True, set the modified flag for this file
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        for window in self.windowList:
            window.updateTree()
            window.updateRightViews()
        if setModified:
            self.setModified()
        QApplication.restoreOverrideCursor()

    def updateCommandsAvail(self):
        """Set commands available based on node selections.
        """
        pass

    def updateWindowCaptions(self):
        """Update the caption for all windows.
        """
        for window in self.windowList:
            window.setCaption(self.filePathObj)

    def setModified(self, modified=True):
        """Set the modified flag on this file and update commands available.

        Arguments:
            modified -- the modified state to set
        """
        if modified != self.modified:
            self.modified = modified
            self.allActions['FileSave'].setEnabled(modified)

    def currentSelectionModel(self):
        """Return the current tree's selection model.
        """
        return self.activeWindow.treeView.selectionModel()

    def setActiveWin(self, window):
        """When a window is activated, stores it and emits a signal.

        Arguments:
            window -- the new active window
        """
        self.activeWindow = window
        self.controlActivated.emit(self)

    def checkWindowClose(self, window):
        """Check for modified files and delete ref when a window is closing.

        Arguments:
            window -- the window being closed
        """
        if len(self.windowList) > 1:
            self.windowList.remove(window)
            window.allowCloseFlag = True
            # # keep ref until Qt window can fully close
            # self.oldWindow = window
        elif self.checkSaveChanges():
            window.allowCloseFlag = True
            self.controlClosed.emit(self)
        else:
            window.allowCloseFlag = False

    def checkSaveChanges(self):
        """Ask for save if doc modified, return True if OK to continue.

        Save this doc if directed.
        Return True if not modified, if saved or if discarded.
        Return False on cancel.
        """
        if not self.modified or len(self.windowList) > 1:
            return True
        promptText = (_('Save changes to {}?').format(str(self.filePathObj))
                      if self.filePathObj else _('Save changes?'))
        ans = QMessageBox.information(self.activeWindow, 'TreeLine',
                                      promptText,
                                      QMessageBox.Save | QMessageBox.Discard |
                                      QMessageBox.Cancel, QMessageBox.Save)
        if ans == QMessageBox.Save:
            self.fileSave()
        elif ans == QMessageBox.Cancel:
            return False
        return True

    def closeWindows(self):
        """Close this control's windows prior to quiting the application.
        """
        for window in self.windowList:
            window.close()

    def setupActions(self):
        """Add the actions for contols at the local level.

        These actions affect an individual file, possibly in multiple windows.
        """
        localActions = {}

        fileSaveAct = QAction(_('&Save'), self, toolTip=_('Save File'),
                              statusTip=_('Save the current file'))
        fileSaveAct.setEnabled(False)
        fileSaveAct.triggered.connect(self.fileSave)
        localActions['FileSave'] = fileSaveAct

        fileSaveAsAct = QAction(_('Save &As...'), self,
                                statusTip=_('Save the file with a new name'))
        fileSaveAsAct.triggered.connect(self.fileSaveAs)
        localActions['FileSaveAs'] = fileSaveAsAct


        editUndoAct = QAction(_('&Undo'), self,
                              statusTip=_('Undo the previous action'))
        editUndoAct.triggered.connect(self.editUndo)
        localActions['EditUndo'] = editUndoAct

        editRedoAct = QAction(_('&Redo'), self,
                              statusTip=_('Redo the previous undo'))
        editRedoAct.triggered.connect(self.editRedo)
        localActions['EditRedo'] = editRedoAct

        for name, action in localActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions.getValue(name)
            if not key.isEmpty():
                action.setShortcut(key)
        self.allActions.update(localActions)

    def fileSave(self, backupFile=False):
        """Save the currently active file.

        Arguments:
            backupFile -- if True, write auto-save backup file instead
        """
        if not self.filePathObj or self.imported:
            self.fileSaveAs()
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        savePathObj = self.filePathObj
        if backupFile:
            savePathObj = pathlib.Path(str(savePathObj) + '~')
        try:
            with savePathObj.open('w', encoding='utf-8', newline='\n') as f:
                self.structure.storeFile(f)
        except IOError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.activeWindow, 'TreeLine',
                                _('Error - could not write to {}').
                                format(str(savePathObj)))
        else:
            QApplication.restoreOverrideCursor()
            if not backupFile:
                self.setModified(False)
                self.imported = False
                self.activeWindow.statusBar().showMessage(_('File saved'),
                                                          3000)

    def fileSaveAs(self):
        """Prompt for a new file name and save the file.
        """
        oldPathObj = self.filePathObj
        oldModifiedFlag = self.modified
        oldImportFlag = self.imported
        self.modified = True
        self.imported = False
        filters = ';;'.join((globalref.fileFilters['trl'],
                             globalref.fileFilters['trlgz'],
                             globalref.fileFilters['trlenc']))
        initFilter = globalref.fileFilters['trl']
        defaultPathObj = globalref.mainControl.defaultPathObj()
        defaultPathObj = defaultPathObj.with_suffix('.trl')
        newPath, selectFilter = (QFileDialog.
                                 getSaveFileName(self.activeWindow,
                                                 _('TreeLine - Save As'),
                                                 str(defaultPathObj),
                                                 filters, initFilter))
        if newPath:
            self.filePathObj = pathlib.Path(newPath)
            if not self.filePathObj.suffix:
                self.filePathObj.with_suffix('.trl')
            self.fileSave()
            if not self.modified:
                self.updateWindowCaptions()
                return
        self.filePathObj = oldPathObj
        self.modified = oldModifiedFlag
        self.imported = oldImportFlag

    def editUndo(self):
        """Undo the previous action and update the views.
        """
        self.structure.undoList.undo()
        self.updateAll(False)

    def editRedo(self):
        """Redo the previous undo and update the views.
        """
        self.structure.redoList.undo()
        self.updateAll(False)

    def windowNew(self, offset=30):
        """Open a new window for this file.

        Arguments:
            offset -- location offset from previously saved position
        """
        window = treewindow.TreeWindow(self.model, self.allActions)
        self.setWindowSignals(window)
        self.windowList.append(window)
        window.setCaption(self.filePathObj)
        # window.restoreWindowGeom(offset)
        self.activeWindow = window
        window.show()
