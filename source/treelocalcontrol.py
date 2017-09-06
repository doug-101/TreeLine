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
import json
import os
import sys
import gzip
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QDialog,
                             QFileDialog, QMenu, QMessageBox)
import treemaincontrol
import treestructure
import treemodel
import treewindow
import exports
import miscdialogs
import printdata
import matheval
import undo
import p3
import globalref


class TreeLocalControl(QObject):
    """Class to handle controls local to a model/view combination.

    Provides methods for all local controls and stores a model & windows.
    """
    controlActivated = pyqtSignal(QObject)
    controlClosed = pyqtSignal(QObject)
    def __init__(self, allActions, fileObj=None, treeStruct=None,
                 forceNewWindow=False, parent=None):
        """Initialize the local tree controls.

        Use an imported structure if given or open the file if path is given.
        Always creates a new window.
        Arguments:
            allActions -- a dict containing the upper level actions
            fileObj -- the path object or file object to open, if given
            treeStruct -- an imported tree structure file, if given
            forceNewWindow -- if True, use a new window regardless of option
            parent -- a parent object if given
        """
        super().__init__(parent)
        self.printData = printdata.PrintData(self)
        self.spellCheckLang = ''
        self.allActions = allActions.copy()
        self.setupActions()
        self.filePathObj = (pathlib.Path(fileObj.name) if
                            hasattr(fileObj, 'read') else fileObj)
        if treeStruct:
            self.structure = treeStruct
        elif fileObj:
            if  hasattr(fileObj, 'read'):
                fileData = json.load(fileObj)
            else:
                with fileObj.open('r', encoding='utf-8') as f:
                    fileData = json.load(f)
            self.structure = treestructure.TreeStructure(fileData)
            self.printData.readData(fileData['properties'])
            self.spellCheckLang = fileData['properties'].get('spellchk', '')
        else:
            self.structure = treestructure.TreeStructure(addDefaults=True)
        fileInfoFormat = self.structure.treeFormats.fileInfoFormat
        fileInfoFormat.updateFileInfo(self.filePathObj,
                                      self.structure.fileInfoNode)
        self.model = treemodel.TreeModel(self.structure)
        self.model.treeModified.connect(self.updateRightViews)

        self.modified = False
        self.imported = False
        self.compressed = False
        self.encrypted = False
        self.windowList = []
        self.activeWindow = None
        self.findReplaceSpotRef = (None, 0)
        QApplication.clipboard().dataChanged.connect(self.updateCommandsAvail)
        self.structure.undoList = undo.UndoRedoList(self.
                                                    allActions['EditUndo'],
                                                    self)
        self.structure.redoList = undo.UndoRedoList(self.
                                                    allActions['EditRedo'],
                                                    self)
        self.structure.undoList.altListRef = self.structure.redoList
        self.structure.redoList.altListRef = self.structure.undoList
        if not globalref.mainControl.activeControl:
            self.windowNew(offset=0)
        elif forceNewWindow or globalref.genOptions['OpenNewWindow']:
            self.windowNew()
        else:
            oldControl = globalref.mainControl.activeControl
            window = oldControl.activeWindow
            if len(oldControl.windowList) > 1:
                oldControl.windowList.remove(window)
            else:
                oldControl.controlClosed.emit(oldControl)
            window.resetTreeModel(self.model)
            # set first spot current to match cases with a new window
            window.treeView.selectionModel().setCurrentSpot(self.structure.
                                                            rootSpots()[0])
            self.setWindowSignals(window, True)
            window.updateActions(self.allActions)
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
        window.setExternalSignals()

    def updateTreeNode(self, node, setModified=True):
        """Update the full tree in all windows.

        Also update right views in secondary windows.
        Arguments:
            node -- the node to be updated
            setModified -- if True, set the modified flag for this file
        """
        if node.setConditionalType(self.structure):
            self.activeWindow.updateRightViews(outputOnly=True)
        if (self.structure.treeFormats.mathFieldRefDict and
            node.updateNodeMathFields(self.structure.treeFormats)):
            self.activeWindow.updateRightViews(outputOnly=True)
            if globalref.genOptions['ShowMath']:
                self.activeWindow.refreshDataEditViews()
        for window in self.windowList:
            window.updateTreeNode(node)
            if window.treeFilterView:
                window.treeFilterView.updateItem(node)
        if setModified:
            self.setModified()

    def updateTree(self, setModified=True):
        """Update the full tree in all windows.

        Also update right views in secondary windows.
        Arguments:
            setModified -- if True, set the modified flag for this file
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        typeChanges = 0
        if self.structure.treeFormats.conditionalTypes:
            for node in self.structure.childList:
                typeChanges += node.setDescendantConditionalTypes(self.
                                                                  structure)
        self.updateAllMathFields()
        for window in self.windowList:
            window.updateTree()
            if window != self.activeWindow or typeChanges:
                window.updateRightViews()
            if window.treeFilterView:
                window.treeFilterView.updateContents()
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
        if self.structure.treeFormats.conditionalTypes:
            for node in self.structure.childList:
                node.setDescendantConditionalTypes(self.structure)
        self.updateAllMathFields()
        for window in self.windowList:
            window.updateTree()
            if window.treeFilterView:
                window.treeFilterView.updateContents()
            window.updateRightViews()
        self.updateCommandsAvail()
        if setModified:
            self.setModified()
        QApplication.restoreOverrideCursor()

    def updateAllMathFields(self):
        """Recalculate all math fields in the entire tree.
        """
        for eqnRefDict in self.structure.treeFormats.mathLevelList:
            if list(eqnRefDict.values())[0][0].evalDirection != (matheval.
                                                                 EvalDir.
                                                                 upward):
                for node in self.structure.descendantGen():
                    for eqnRef in eqnRefDict.get(node.formatRef.name, []):
                        node.data[eqnRef.eqnField.name] = (eqnRef.eqnField.
                                                           equationValue(node))
            else:
                spot = self.structure.structSpot().lastDescendantSpot()
                while spot:
                    node = spot.nodeRef
                    for eqnRef in eqnRefDict.get(node.formatRef.name, []):
                        node.data[eqnRef.eqnField.name] = (eqnRef.eqnField.
                                                           equationValue(node))
                    spot = spot.prevTreeSpot()

    def updateCommandsAvail(self):
        """Set commands available based on node selections.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        rootSpots = [spot for spot in selSpots if not
                     spot.parentSpot.parentSpot]
        hasGrandParent = (len(selSpots) and len(rootSpots) == 0 and
                          None not in [spot.parentSpot.parentSpot.parentSpot
                                       for spot in selSpots])
        hasPrevSibling = (len(selSpots) and None not in
                          [spot.prevSiblingSpot() for spot in selSpots])
        hasNextSibling = (len(selSpots) and None not in
                          [spot.nextSiblingSpot() for spot in selSpots])
        mime = QApplication.clipboard().mimeData()
        hasData = len(mime.data('application/json')) > 0
        hasText = len(mime.data('text/plain')) > 0
        self.allActions['EditPaste'].setEnabled(hasData or hasText)
        self.allActions['EditPasteChild'].setEnabled(hasData)
        self.allActions['EditPasteBefore'].setEnabled(hasData and
                                                      len(selSpots) > 0)
        self.allActions['EditPasteAfter'].setEnabled(hasData and
                                                     len(selSpots) > 0)
        self.allActions['EditPasteCloneChild'].setEnabled(hasData)
        self.allActions['EditPasteCloneBefore'].setEnabled(hasData and
                                                           len(selSpots) > 0)
        self.allActions['EditPasteCloneAfter'].setEnabled(hasData and
                                                          len(selSpots) > 0)
        self.allActions['NodeRename'].setEnabled(len(selSpots) == 1)
        self.allActions['NodeInsertBefore'].setEnabled(len(selSpots) > 0)
        self.allActions['NodeInsertAfter'].setEnabled(len(selSpots) > 0)
        self.allActions['NodeDelete'].setEnabled(len(selSpots) > 0 and
                                                 len(rootSpots) <
                                                 len(self.structure.childList))
        self.allActions['NodeIndent'].setEnabled(hasPrevSibling)
        self.allActions['NodeUnindent'].setEnabled(hasGrandParent)
        self.allActions['NodeMoveUp'].setEnabled(hasPrevSibling)
        self.allActions['NodeMoveDown'].setEnabled(hasNextSibling)
        self.allActions['NodeMoveFirst'].setEnabled(hasPrevSibling)
        self.allActions['NodeMoveLast'].setEnabled(hasNextSibling)
        self.allActions['DataNodeType'].parent().setEnabled(len(selSpots) > 0)
        if self.activeWindow.treeFilterView:
            self.allActions['NodeInsertBefore'].setEnabled(False)
            self.allActions['NodeInsertAfter'].setEnabled(False)
            self.allActions['NodeAddChild'].setEnabled(False)
            self.allActions['NodeIndent'].setEnabled(False)
            self.allActions['NodeUnindent'].setEnabled(False)
            self.allActions['NodeMoveUp'].setEnabled(False)
            self.allActions['NodeMoveDown'].setEnabled(False)
            self.allActions['NodeMoveFirst'].setEnabled(False)
            self.allActions['NodeMoveLast'].setEnabled(False)
        self.activeWindow.updateCommandsAvail()

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

    def expandRootNodes(self, maxNum=5):
        """Expand root node if there are fewer than the maximum.

        Arguments:
            maxNum -- only expand if there are fewer root nodes than this.
        """
        if len(self.structure.childList) < maxNum:
            treeView = self.activeWindow.treeView
            for spot in self.structure.rootSpots():
                treeView.expandSpot(spot)

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
        self.updateCommandsAvail()

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

    def windowActions(self, startNum=1, active=False):
        """Return a list of window menu actions to select this file's windows.

        Arguments:
            startNum -- where to start numbering the action names
            active -- if True, activate the current active window
        """
        actions = []
        maxActionPathLength = 30
        abbrevPath = str(self.filePathObj)
        if len(abbrevPath) > maxActionPathLength:
            truncLength = maxActionPathLength - 3
            pos = abbrevPath.find(os.sep, len(abbrevPath) - truncLength)
            if pos < 0:
                pos = len(abbrevPath) - truncLength
            abbrevPath = '...' + abbrevPath[pos:]
        for window in self.windowList:
            action = QAction('&{0:d} {1}'.format(startNum, abbrevPath), self,
                             statusTip=str(self.filePathObj), checkable=True)
            action.triggered.connect(window.activateAndRaise)
            if active and window == self.activeWindow:
                action.setChecked(True)
            actions.append(action)
            startNum += 1
        return actions

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

        fileExportAct = QAction(_('&Export...'), self,
                       statusTip=_('Export the file in various other formats'))
        fileExportAct.triggered.connect(self.fileExport)
        localActions['FileExport'] = fileExportAct

        filePropertiesAct = QAction(_('Prop&erties...'), self,
            statusTip=_('Set file parameters like compression and encryption'))
        filePropertiesAct.triggered.connect(self.fileProperties)
        localActions['FileProperties'] = filePropertiesAct

        filePrintSetupAct = QAction(_('P&rint Setup...'), self,
              statusTip=_('Set margins, page size and other printing options'))
        filePrintSetupAct.triggered.connect(self.printData.printSetup)
        localActions['FilePrintSetup'] = filePrintSetupAct

        filePrintPreviewAct = QAction(_('Print Pre&view...'), self,
                             statusTip=_('Show a preview of printing results'))
        filePrintPreviewAct.triggered.connect(self.printData.printPreview)
        localActions['FilePrintPreview'] = filePrintPreviewAct

        filePrintAct = QAction(_('&Print...'), self,
                     statusTip=_('Print tree output based on current options'))
        filePrintAct.triggered.connect(self.printData.filePrint)
        localActions['FilePrint'] = filePrintAct

        filePrintPdfAct = QAction(_('Print &to PDF...'), self,
                    statusTip=_('Export to PDF with current printing options'))
        filePrintPdfAct.triggered.connect(self.printData.filePrintPdf)
        localActions['FilePrintPdf'] = filePrintPdfAct

        editUndoAct = QAction(_('&Undo'), self,
                              statusTip=_('Undo the previous action'))
        editUndoAct.triggered.connect(self.editUndo)
        localActions['EditUndo'] = editUndoAct

        editRedoAct = QAction(_('&Redo'), self,
                              statusTip=_('Redo the previous undo'))
        editRedoAct.triggered.connect(self.editRedo)
        localActions['EditRedo'] = editRedoAct

        editCutAct = QAction(_('Cu&t'), self,
                        statusTip=_('Cut the branch or text to the clipboard'))
        editCutAct.triggered.connect(self.editCut)
        localActions['EditCut'] = editCutAct

        editCopyAct = QAction(_('&Copy'), self,
                       statusTip=_('Copy the branch or text to the clipboard'))
        editCopyAct.triggered.connect(self.editCopy)
        localActions['EditCopy'] = editCopyAct

        editPasteAct = QAction(_('&Paste'), self,
                         statusTip=_('Paste nodes or text from the clipboard'))
        editPasteAct.triggered.connect(self.editPaste)
        localActions['EditPaste'] = editPasteAct

        editPastePlainAct = QAction(_('Pa&ste Plain Text'), self,
                    statusTip=_('Paste non-formatted text from the clipboard'))
        editPastePlainAct.setEnabled(False)
        localActions['EditPastePlain'] = editPastePlainAct

        editPasteChildAct = QAction(_('Paste C&hild'), self,
                          statusTip=_('Paste a child node from the clipboard'))
        editPasteChildAct.triggered.connect(self.editPasteChild)
        localActions['EditPasteChild'] = editPasteChildAct

        editPasteBeforeAct = QAction(_('Paste Sibling &Before'), self,
                               statusTip=_('Paste a sibling before selection'))
        editPasteBeforeAct.triggered.connect(self.editPasteBefore)
        localActions['EditPasteBefore'] = editPasteBeforeAct

        editPasteAfterAct = QAction(_('Paste Sibling &After'), self,
                                statusTip=_('Paste a sibling after selection'))
        editPasteAfterAct.triggered.connect(self.editPasteAfter)
        localActions['EditPasteAfter'] = editPasteAfterAct

        editPasteCloneChildAct = QAction(_('Paste Cl&oned Child'), self,
                         statusTip=_('Paste a child clone from the clipboard'))
        editPasteCloneChildAct.triggered.connect(self.editPasteCloneChild)
        localActions['EditPasteCloneChild'] = editPasteCloneChildAct

        editPasteCloneBeforeAct = QAction(_('Paste Clo&ned Sibling Before'),
                   self, statusTip=_('Paste a sibling clone before selection'))
        editPasteCloneBeforeAct.triggered.connect(self.editPasteCloneBefore)
        localActions['EditPasteCloneBefore'] = editPasteCloneBeforeAct

        editPasteCloneAfterAct = QAction(_('Paste Clone&d Sibling After'),
                    self, statusTip=_('Paste a sibling clone after selection'))
        editPasteCloneAfterAct.triggered.connect(self.editPasteCloneAfter)
        localActions['EditPasteCloneAfter'] = editPasteCloneAfterAct

        nodeRenameAct = QAction(_('&Rename'), self,
                            statusTip=_('Rename the current tree entry title'))
        nodeRenameAct.triggered.connect(self.nodeRename)
        localActions['NodeRename'] = nodeRenameAct

        nodeAddChildAct = QAction(_('Add &Child'), self,
                               statusTip=_('Add new child to selected parent'))
        nodeAddChildAct.triggered.connect(self.nodeAddChild)
        localActions['NodeAddChild'] = nodeAddChildAct

        nodeInBeforeAct = QAction(_('Insert Sibling &Before'), self,
                            statusTip=_('Insert new sibling before selection'))
        nodeInBeforeAct.triggered.connect(self.nodeInBefore)
        localActions['NodeInsertBefore'] = nodeInBeforeAct

        nodeInAfterAct = QAction(_('Insert Sibling &After'), self,
                            statusTip=_('Insert new sibling after selection'))
        nodeInAfterAct.triggered.connect(self.nodeInAfter)
        localActions['NodeInsertAfter'] = nodeInAfterAct

        nodeDeleteAct = QAction(_('&Delete Node'), self,
                                statusTip=_('Delete the selected nodes'))
        nodeDeleteAct.triggered.connect(self.nodeDelete)
        localActions['NodeDelete'] = nodeDeleteAct

        nodeIndentAct = QAction(_('&Indent Node'), self,
                                      statusTip=_('Indent the selected nodes'))
        nodeIndentAct.triggered.connect(self.nodeIndent)
        localActions['NodeIndent'] = nodeIndentAct

        nodeUnindentAct = QAction(_('&Unindent Node'), self,
                                    statusTip=_('Unindent the selected nodes'))
        nodeUnindentAct.triggered.connect(self.nodeUnindent)
        localActions['NodeUnindent'] = nodeUnindentAct

        nodeMoveUpAct = QAction(_('&Move Up'), self,
                                      statusTip=_('Move the selected nodes up'))
        nodeMoveUpAct.triggered.connect(self.nodeMoveUp)
        localActions['NodeMoveUp'] = nodeMoveUpAct

        nodeMoveDownAct = QAction(_('M&ove Down'), self,
                                   statusTip=_('Move the selected nodes down'))
        nodeMoveDownAct.triggered.connect(self.nodeMoveDown)
        localActions['NodeMoveDown'] = nodeMoveDownAct

        nodeMoveFirstAct = QAction(_('Move &First'), self,
               statusTip=_('Move the selected nodes to be the first children'))
        nodeMoveFirstAct.triggered.connect(self.nodeMoveFirst)
        localActions['NodeMoveFirst'] = nodeMoveFirstAct

        nodeMoveLastAct = QAction(_('Move &Last'), self,
                statusTip=_('Move the selected nodes to be the last children'))
        nodeMoveLastAct.triggered.connect(self.nodeMoveLast)
        localActions['NodeMoveLast'] = nodeMoveLastAct

        title = _('&Set Node Type')
        key = globalref.keyboardOptions['DataNodeType']
        if not key.isEmpty():
            title = '{0}  ({1})'.format(title, key.toString())
        self.typeSubMenu = QMenu(title,
                           statusTip=_('Set the node type for selected nodes'))
        self.typeSubMenu.aboutToShow.connect(self.loadTypeSubMenu)
        self.typeSubMenu.triggered.connect(self.dataSetType)
        typeContextMenuAct = QAction(_('Set Node Type'), self.typeSubMenu)
        typeContextMenuAct.triggered.connect(self.showTypeContextMenu)
        localActions['DataNodeType'] = typeContextMenuAct

        formatBoldAct = QAction(_('&Bold Font'), self,
                       statusTip=_('Set the current or selected font to bold'),
                       checkable=True)
        formatBoldAct.setEnabled(False)
        localActions['FormatBoldFont'] = formatBoldAct

        formatItalicAct = QAction(_('&Italic Font'), self,
                     statusTip=_('Set the current or selected font to italic'),
                     checkable=True)
        formatItalicAct.setEnabled(False)
        localActions['FormatItalicFont'] = formatItalicAct

        formatUnderlineAct = QAction(_('U&nderline Font'), self,
                  statusTip=_('Set the current or selected font to underline'),
                  checkable=True)
        formatUnderlineAct.setEnabled(False)
        localActions['FormatUnderlineFont'] = formatUnderlineAct

        title = _('&Font Size')
        key = globalref.keyboardOptions['FormatFontSize']
        if not key.isEmpty():
            title = '{0}  ({1})'.format(title, key.toString())
        self.fontSizeSubMenu = QMenu(title,
                       statusTip=_('Set size of the current or selected text'))
        sizeActions = QActionGroup(self)
        for size in (_('Small'), _('Default'), _('Large'), _('Larger'),
                     _('Largest')):
            action = QAction(size, sizeActions)
            action.setCheckable(True)
        self.fontSizeSubMenu.addActions(sizeActions.actions())
        self.fontSizeSubMenu.setEnabled(False)
        fontSizeContextMenuAct = QAction(_('Set Font Size'),
                                         self.fontSizeSubMenu)
        localActions['FormatFontSize'] = fontSizeContextMenuAct

        formatColorAct =  QAction(_('Font C&olor...'), self,
                  statusTip=_('Set the color of the current or selected text'))
        formatColorAct.setEnabled(False)
        localActions['FormatFontColor'] = formatColorAct

        formatExtLinkAct = QAction(_('&External Link...'), self,
                              statusTip=_('Add or modify an extrnal web link'))
        formatExtLinkAct.setEnabled(False)
        localActions['FormatExtLink'] = formatExtLinkAct

        formatIntLinkAct = QAction(_('Internal &Link...'), self,
                            statusTip=_('Add or modify an internal node link'))
        formatIntLinkAct.setEnabled(False)
        localActions['FormatIntLink'] = formatIntLinkAct

        formatClearFormatAct =  QAction(_('Clear For&matting'), self,
                      statusTip=_('Clear current or selected text formatting'))
        formatClearFormatAct.setEnabled(False)
        localActions['FormatClearFormat'] = formatClearFormatAct

        winNewAct = QAction(_('&New Window'), self,
                            statusTip=_('Open a new window for the same file'))
        winNewAct.triggered.connect(self.windowNew)
        localActions['WinNewWindow'] = winNewAct

        for name, action in localActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions[name]
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
        fileData = self.structure.fileData()
        fileData['properties'].update(self.printData.fileData())
        if self.spellCheckLang:
            fileData['properties']['spellchk'] = self.spellCheckLang
        if not self.compressed and not self.encrypted:
            try:
                with savePathObj.open('w', encoding='utf-8',
                                      newline='\n') as f:
                    json.dump(fileData, f, indent=3, sort_keys=True)
            except IOError:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self.activeWindow, 'TreeLine',
                                    _('Error - could not write to {}').
                                    format(str(savePathObj)))
                return
        else:
            data = json.dumps(fileData, indent=3, sort_keys=True).encode()
            if self.compressed:
                data = gzip.compress(data)
            if self.encrypted:
                password = (globalref.mainControl.passwords.
                            get(self.filePathObj, ''))
                if not password:
                    QApplication.restoreOverrideCursor()
                    dialog = miscdialogs.PasswordDialog(True, '',
                                                        self.activeWindow)
                    if dialog.exec_() != QDialog.Accepted:
                        return
                    QApplication.setOverrideCursor(Qt.WaitCursor)
                    password = dialog.password
                    if miscdialogs.PasswordDialog.remember:
                        globalref.mainControl.passwords[self.
                                                        filePathObj] = password
                data = (treemaincontrol.encryptPrefix +
                        p3.p3_encrypt(data, password.encode()))
            try:
                with savePathObj.open('wb') as f:
                    f.write(data)
            except IOError:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self.activeWindow, 'TreeLine',
                                    _('Error - could not write to {}').
                                    format(str(savePathObj)))
                return
        QApplication.restoreOverrideCursor()
        if not backupFile:
            fileInfoFormat = self.structure.treeFormats.fileInfoFormat
            fileInfoFormat.updateFileInfo(self.filePathObj,
                                          self.structure.fileInfoNode)
            self.setModified(False)
            self.imported = False
            self.activeWindow.statusBar().showMessage(_('File saved'), 3000)

    def fileSaveAs(self):
        """Prompt for a new file name and save the file.
        """
        oldPathObj = self.filePathObj
        oldModifiedFlag = self.modified
        oldImportFlag = self.imported
        self.modified = True
        self.imported = False
        filters = ';;'.join((globalref.fileFilters['trlnsave'],
                             globalref.fileFilters['trlngz'],
                             globalref.fileFilters['trlnenc']))
        initFilter = globalref.fileFilters['trlnsave']
        defaultPathObj = globalref.mainControl.defaultPathObj()
        defaultPathObj = defaultPathObj.with_suffix('.trln')
        newPath, selectFilter = (QFileDialog.
                                 getSaveFileName(self.activeWindow,
                                                 _('TreeLine - Save As'),
                                                 str(defaultPathObj),
                                                 filters, initFilter))
        if newPath:
            self.filePathObj = pathlib.Path(newPath)
            if not self.filePathObj.suffix:
                self.filePathObj = self.filePathObj.with_suffix('.trln')
            if selectFilter != initFilter:
                self.compressed = (selectFilter ==
                                   globalref.fileFilters['trlngz'])
                self.encrypted = (selectFilter ==
                                  globalref.fileFilters['trlnenc'])
            self.fileSave()
            if not self.modified:
                globalref.mainControl.recentFiles.addItem(self.filePathObj)
                self.updateWindowCaptions()
                return
        self.filePathObj = oldPathObj
        self.modified = oldModifiedFlag
        self.imported = oldImportFlag

    def fileExport(self):
        """Export the file in various other formats.
        """
        exportControl = exports.ExportControl(self.structure,
                                              self.currentSelectionModel(),
                                              globalref.mainControl.
                                              defaultPathObj(), self.printData)
        try:
            exportControl.interactiveExport()
        except IOError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self.activeWindow, 'TreeLine',
                                _('Error - could not write to file'))

    def fileProperties(self):
        """Show dialog to set file parameters like compression and encryption.
        """
        # origZeroBlanks = self.model.mathZeroBlanks
        dialog = miscdialogs.FilePropertiesDialog(self, self.activeWindow)
        if dialog.exec_() == QDialog.Accepted:
            self.setModified()
            # if self.model.mathZeroBlanks != origZeroBlanks:
                # self.updateAll(False)

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

    def editCut(self):
        """Cut the branch or text to the clipboard.
        """
        widget = QApplication.focusWidget()
        try:
            if widget.hasSelectedText():
                widget.cut()
                return
        except AttributeError:
            pass
        self.currentSelectionModel().copySelectedNodes()
        self.nodeDelete()

    def editCopy(self):
        """Copy the branch or text to the clipboard.

        Copy from any selection in non-focused output view, or copy from
        any focused editor, or copy from tree.
        """
        widgets = [QApplication.focusWidget()]
        splitter = self.activeWindow.rightTabs.currentWidget()
        if splitter == self.activeWindow.outputSplitter:
            widgets[0:0] = [splitter.widget(0), splitter.widget(1)]
        for widget in widgets:
            try:
                if widget.hasSelectedText():
                    widget.copy()
                    return
            except AttributeError:
                pass
        self.currentSelectionModel().copySelectedNodes()

    def editPaste(self):
        """Paste nodes or text from the clipboard.
        """
        if self.activeWindow.treeView.hasFocus():
            self.editPasteChild()
        else:
            widget = QApplication.focusWidget()
            try:
                widget.paste()
            except AttributeError:
                pass

    def editPasteChild(self):
        """Paste a child node from the clipboard.
        """
        if (self.currentSelectionModel().selectedSpots().
            pasteChild(self.structure, self.activeWindow.treeView)):
            self.updateAll()

    def editPasteBefore(self):
        """Paste a sibling before selection.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        if selSpots.pasteSibling(self.structure):
            self.currentSelectionModel().selectSpots(selSpots, False)
            self.updateAll()

    def editPasteAfter(self):
        """Paste a sibling after selection.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        if selSpots.pasteSibling(self.structure, False):
            self.currentSelectionModel().selectSpots(selSpots, False)
            self.updateAll()

    def editPasteCloneChild(self):
        """Paste a child clone from the clipboard.
        """
        if (self.currentSelectionModel().selectedSpots().
            pasteCloneChild(self.structure, self.activeWindow.treeView)):
            self.updateAll()

    def editPasteCloneBefore(self):
        """Paste a sibling clone before selection.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        if selSpots.pasteCloneSibling(self.structure):
            self.currentSelectionModel().selectSpots(selSpots, False)
            self.updateAll()

    def editPasteCloneAfter(self):
        """Paste a sibling clone after selection.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        if selSpots.pasteCloneSibling(self.structure, False):
            self.currentSelectionModel().selectSpots(selSpots, False)
            self.updateAll()

    def nodeRename(self):
        """Start the rename editor in the selected tree node.
        """
        if self.activeWindow.treeFilterView:
            self.activeWindow.treeFilterView.editItem(self.activeWindow.
                                                      treeFilterView.
                                                      currentItem())
        else:
            self.activeWindow.treeView.endEditing()
            self.activeWindow.treeView.edit(self.currentSelectionModel().
                                            currentIndex())

    def nodeAddChild(self):
        """Add new child to selected parent.
        """
        self.activeWindow.treeView.endEditing()
        selSpots = self.currentSelectionModel().selectedSpots()
        newSpots = selSpots.addChild(self.structure,
                                     self.activeWindow.treeView)
        if globalref.genOptions['RenameNewNodes']:
            self.currentSelectionModel().selectSpots(newSpots, False)
            if len(newSpots) == 1:
                self.updateAll()
                self.activeWindow.treeView.edit(newSpots[0].index(self.model))
                return
        self.updateAll()

    def nodeInBefore(self):
        """Insert new sibling before selection.
        """
        self.activeWindow.treeView.endEditing()
        selSpots = self.currentSelectionModel().selectedSpots()
        newSpots = selSpots.insertSibling(self.structure)
        if globalref.genOptions['RenameNewNodes']:
            self.currentSelectionModel().selectSpots(newSpots, False)
            if len(newSpots) == 1:
                self.updateAll()
                self.activeWindow.treeView.edit(newSpots[0].index(self.model))
                return
        self.updateAll()

    def nodeInAfter(self):
        """Insert new sibling after selection.
        """
        self.activeWindow.treeView.endEditing()
        selSpots = self.currentSelectionModel().selectedSpots()
        newSpots = selSpots.insertSibling(self.structure, False)
        if globalref.genOptions['RenameNewNodes']:
            self.currentSelectionModel().selectSpots(newSpots, False)
            if len(newSpots) == 1:
                self.updateAll()
                self.activeWindow.treeView.edit(newSpots[0].index(self.model))
                return
        self.updateAll()

    def nodeDelete(self):
        """Delete the selected nodes.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        if selSpots:
            # avoid problems with temporarily invalid selection
            self.currentSelectionModel().selectSpots([], False)
            nextSel = selSpots.delete(self.structure)
            self.currentSelectionModel().selectSpots([nextSel], False)
            self.updateAll()

    def nodeIndent(self):
        """Indent the selected nodes.

        Makes them children of their previous siblings.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        newSpots = selSpots.indent(self.structure, self.activeWindow.treeView)
        self.currentSelectionModel().selectSpots(newSpots, False)
        self.updateAll()

    def nodeUnindent(self):
        """Unindent the selected nodes.

        Makes them their parent's next sibling.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        newSpots = selSpots.unindent(self.structure)
        self.currentSelectionModel().selectSpots(newSpots, False)
        self.updateAll()

    def nodeMoveUp(self):
        """Move the selected nodes upward in the sibling list.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        selSpots.move(self.structure)
        self.currentSelectionModel().selectSpots(selSpots, False)
        self.updateAll()

    def nodeMoveDown(self):
        """Move the selected nodes downward in the sibling list.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        selSpots.move(self.structure, False)
        self.currentSelectionModel().selectSpots(selSpots, False)
        self.updateAll()

    def nodeMoveFirst(self):
        """Move the selected nodes to be the first children.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        selSpots.moveToEnd(self.structure)
        self.currentSelectionModel().selectSpots(selSpots, False)
        self.updateAll()

    def nodeMoveLast(self):
        """Move the selected nodes to be the last children.
        """
        selSpots = self.currentSelectionModel().selectedSpots()
        selSpots.moveToEnd(self.structure, False)
        self.currentSelectionModel().selectSpots(selSpots, False)
        self.updateAll()

    def dataSetType(self, action):
        """Change the type of selected nodes based on a menu selection.

        Arguments:
            action -- the menu action containing the new type name
        """
        newType = action.toolTip()   # gives menu name without the accelerator
        nodes = [node for node in self.currentSelectionModel().selectedNodes()
                 if node.formatRef.name != newType]
        if nodes:
            undo.TypeUndo(self.structure.undoList, nodes)
            for node in nodes:
                node.changeDataType(self.structure.treeFormats[newType])
        self.updateAll()

    def loadTypeSubMenu(self):
        """Update type select submenu with type names and check marks.
        """
        selectTypes = {node.formatRef.name for node in
                       self.currentSelectionModel().selectedNodes()}
        typeNames = self.structure.treeFormats.typeNames()
        self.typeSubMenu.clear()
        usedShortcuts = []
        for name in typeNames:
            shortcutPos = 0
            try:
                while [shortcutPos] in usedShortcuts:
                    shortcutPos += 1
                usedShortcuts.append(name[shortcutPos])
                text = '{0}&{1}'.format(name[:shortcutPos], name[shortcutPos:])
            except IndexError:
                text = name
            action = self.typeSubMenu.addAction(text)
            action.setCheckable(True)
            if name in selectTypes:
                action.setChecked(True)

    def showTypeContextMenu(self):
        """Show a type set menu at the current tree view item.
        """
        self.activeWindow.treeView.showTypeMenu(self.typeSubMenu)

    def findNodesByWords(self, wordList, titlesOnly=False, forward=True):
        """Search for and select nodes that match the word list criteria.

        Called from the text find dialog.
        Returns True if found, otherwise False.
        Arguments:
            wordList -- a list of words or phrases to find
            titleOnly -- search only in the title text if True
            forward -- next if True, previous if False
        """
        currentSpot = self.currentSelectionModel().currentSpot()
        spot = currentSpot
        while True:
            if self.activeWindow.treeFilterView:
                spot = self.activeWindow.treeFilterView.nextPrevSpot(spot,
                                                                     forward)
            else:
                if forward:
                    spot = spot.nextTreeSpot(True)
                else:
                    spot = spot.prevTreeSpot(True)
            if spot is currentSpot:
                return False
            if spot.nodeRef.wordSearch(wordList, titlesOnly, spot):
                self.currentSelectionModel().selectSpots([spot], True, True)
                rightView = self.activeWindow.rightParentView()
                if not rightView:
                    # view update required if (and only if) view is newly shown
                    QApplication.processEvents()
                    rightView = self.activeWindow.rightParentView()
                if rightView:
                    rightView.highlightSearch(wordList=wordList)
                    QApplication.processEvents()
                return True

    def findNodesByRegExp(self, regExpList, titlesOnly=False, forward=True):
        """Search for and select nodes that match the regular exp criteria.

        Called from the text find dialog.
        Returns True if found, otherwise False.
        Arguments:
            regExpList -- a list of regular expression objects
            titleOnly -- search only in the title text if True
            forward -- next if True, previous if False
        """
        currentSpot = self.currentSelectionModel().currentSpot()
        spot = currentSpot
        while True:
            if self.activeWindow.treeFilterView:
                spot = self.activeWindow.treeFilterView.nextPrevSpot(spot,
                                                                     forward)
            else:
                if forward:
                    spot = spot.nextTreeSpot(True)
                else:
                    spot = spot.prevTreeSpot(True)
            if spot is currentSpot:
                return False
            if spot.nodeRef.regExpSearch(regExpList, titlesOnly, spot):
                self.currentSelectionModel().selectSpots([spot], True, True)
                rightView = self.activeWindow.rightParentView()
                if not rightView:
                    # view update required if (and only if) view is newly shown
                    QApplication.processEvents()
                    rightView = self.activeWindow.rightParentView()
                if rightView:
                    rightView.highlightSearch(regExpList=regExpList)
                return True

    def findNodesByCondition(self, conditional, forward=True):
        """Search for and select nodes that match the regular exp criteria.

        Called from the conditional find dialog.
        Returns True if found, otherwise False.
        Arguments:
            conditional -- the Conditional object to be evaluated
            forward -- next if True, previous if False
        """
        currentSpot = self.currentSelectionModel().currentSpot()
        spot = currentSpot
        while True:
            if self.activeWindow.treeFilterView:
                spot = self.activeWindow.treeFilterView.nextPrevSpot(spot,
                                                                     forward)
            else:
                if forward:
                    spot = spot.nextTreeSpot(True)
                else:
                    spot = spot.prevTreeSpot(True)
            if spot is currentSpot:
                return False
            if conditional.evaluate(spot.nodeRef):
                self.currentSelectionModel().selectSpots([spot], True, True)
                return True

    def findNodesForReplace(self, searchText='', regExpObj=None, typeName='',
                            fieldName='', forward=True):
        """Search for & select nodes that match the criteria prior to replace.

        Called from the find replace dialog.
        Returns True if found, otherwise False.
        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            forward -- next if True, previous if False
        """
        currentSpot = self.currentSelectionModel().currentSpot()
        lastFoundSpot, currentNumMatches = self.findReplaceSpotRef
        numMatches = currentNumMatches
        if lastFoundSpot is not currentSpot:
            numMatches = 0
        spot = currentSpot
        if not forward:
            if numMatches == 0:
                numMatches = -1   # find last one if backward
            elif numMatches == 1:
                numMatches = sys.maxsize   # no match if on first one
            else:
                numMatches -= 2
        while True:
            matchedField, numMatches, fieldPos = (spot.nodeRef.
                                                  searchReplace(searchText,
                                                                regExpObj,
                                                                numMatches,
                                                                typeName,
                                                                fieldName))
            if matchedField:
                fieldNum = (spot.nodeRef.formatRef.fieldNames().
                            index(matchedField))
                self.currentSelectionModel().selectSpots([spot], True, True)
                self.activeWindow.rightTabs.setCurrentWidget(self.activeWindow.
                                                             editorSplitter)
                dataView = self.activeWindow.rightParentView()
                if not dataView:
                    # view update required if (and only if) view is newly shown
                    QApplication.processEvents()
                    dataView = self.activeWindow.rightParentView()
                if dataView:
                    dataView.highlightMatch(searchText, regExpObj, fieldNum,
                                            fieldPos - 1)
                self.findReplaceSpotRef = (spot, numMatches)
                return True
            if self.activeWindow.treeFilterView:
                node = self.activeWindow.treeFilterView.nextPrevSpot(spot,
                                                                     forward)
            else:
                if forward:
                    spot = spot.nextTreeSpot(True)
                else:
                    spot = spot.prevTreeSpot(True)
            if spot is currentSpot and currentNumMatches == 0:
                self.findReplaceSpotRef = (None, 0)
                return False
            numMatches = 0 if forward else -1

    def replaceInCurrentNode(self, searchText='', regExpObj=None, typeName='',
                             fieldName='', replaceText=None):
        """Replace the current match in the current node.

        Called from the find replace dialog.
        Returns True if replaced, otherwise False.
        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            replaceText -- if not None, replace a match with this string
        """
        spot = self.currentSelectionModel().currentSpot()
        lastFoundSpot, numMatches = self.findReplaceSpotRef
        if numMatches > 0:
            numMatches -= 1
        if lastFoundSpot is not spot:
            numMatches = 0
        dataUndo = undo.DataUndo(self.structure.undoList, spot.nodeRef)
        matchedField, num1, num2 = (spot.nodeRef.
                                    searchReplace(searchText, regExpObj,
                                                  numMatches, typeName,
                                                  fieldName, replaceText))
        if ((searchText and searchText in replaceText) or
            (regExpObj and r'\g<0>' in replaceText) or
            (regExpObj and regExpObj.pattern.startswith('(') and
             regExpObj.pattern.endswith(')') and r'\1' in replaceText)):
            numMatches += 1    # check for recursive matches
        self.findReplaceSpotRef = (spot, numMatches)
        if matchedField:
            self.updateTreeNode(spot.nodeRef)
            self.updateRightViews()
            return True
        self.structure.undoList.removeLastUndo(dataUndo)
        return False

    def replaceAll(self, searchText='', regExpObj=None, typeName='',
                   fieldName='', replaceText=None):
        """Replace all matches in all nodes.

        Called from the find replace dialog.
        Returns number of matches replaced.
        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            replaceText -- if not None, replace a match with this string
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        dataUndo = undo.BranchUndo(self.structure.undoList,
                                   self.structure.childList)
        totalMatches = 0
        for node in self.structure.nodeDict.values():
            field, matchQty, num = node.searchReplace(searchText, regExpObj,
                                                      0, typeName, fieldName,
                                                      replaceText, True)
            totalMatches += matchQty
        self.findReplaceSpotRef = (None, 0)
        if totalMatches > 0:
            self.updateAll(True)
        else:
            self.structure.undoList.removeLastUndo(dataUndo)
        QApplication.restoreOverrideCursor()
        return totalMatches

    def windowNew(self, checked=False, offset=30):
        """Open a new window for this file.

        Arguments:
            checked -- unused parameter needed by QAction signal
            offset -- location offset from previously saved position
        """
        window = treewindow.TreeWindow(self.model, self.allActions)
        self.setWindowSignals(window)
        self.windowList.append(window)
        window.setCaption(self.filePathObj)
        oldControl = globalref.mainControl.activeControl
        if oldControl:
            oldControl.activeWindow.saveWindowGeom()
        window.restoreWindowGeom(offset)
        self.activeWindow = window
        window.show()
