#!/usr/bin/env python3

#******************************************************************************
# titlelistview.py, provides a class for the title list view
#
# TreeLine, an information storage program
# Copyright (C) 2025, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QPalette, QTextCursor
from PyQt6.QtWidgets import QTextEdit
import treenode
import undo
import globalref


class TitleListView(QTextEdit):
    """Class override for the title list view.
    
    Sets view defaults and updates the content.
    """
    nodeModified = pyqtSignal(treenode.TreeNode)
    treeModified = pyqtSignal()
    shortcutEntered = pyqtSignal(QKeySequence)
    def __init__(self, treeView, isChildView=True, parent=None):
        """Initialize the title list view.

        Arguments:
            treeView - the tree view, needed for the current selection model
            isChildView -- shows selected nodes if false, child nodes if true
            parent -- the parent main window
        """
        super().__init__(parent)
        self.treeView = treeView
        self.isChildView = isChildView
        self.hideChildView = not globalref.genOptions['InitShowChildPane']
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setTabChangesFocus(True)
        self.setUndoRedoEnabled(False)
        self.treeSelectAction = QAction(_('Select in Tree'), self)
        self.treeSelectAction.triggered.connect(self.selectLineInTree)
        self.textChanged.connect(self.readChange)

    def updateContents(self):
        """Reload the view's content if the view is shown.

        Avoids update if view is not visible or has zero height or width.
        """
        selSpots = self.treeView.selectionModel().selectedSpots()
        if self.isChildView:
            if len(selSpots) > 1 or self.hideChildView:
                self.hide()
                return
            if not selSpots:
                # use top node childList from tree structure
                selSpots = [globalref.mainControl.activeControl.structure.
                            structSpot()]
        elif not selSpots:
            self.hide()
            return
        self.show()
        if not self.isVisible() or self.height() == 0 or self.width() == 0:
            return
        if self.isChildView:
            selSpots = selSpots[0].childSpots()
        self.blockSignals(True)
        if selSpots:
            self.setPlainText('\n'.join(spot.nodeRef.title(spot) for spot in
                                        selSpots))
        else:
            self.clear()
        self.blockSignals(False)

    def readChange(self):
        """Update nodes after edited by user.
        """
        textList = [' '.join(text.split()) for text in self.toPlainText().
                    split('\n') if text.strip()]
        selSpots = self.treeView.selectionModel().selectedSpots()
        treeStructure = globalref.mainControl.activeControl.structure
        if self.isChildView:
            if not selSpots:
                selSpots = [treeStructure.structSpot()]
            parentSpot = selSpots[0]
            parent = parentSpot.nodeRef
            selSpots = parentSpot.childSpots()
        if len(selSpots) == len(textList):
            # collect changes first to skip false clone changes
            changes = [(spot.nodeRef, text) for spot, text in
                       zip(selSpots, textList)
                       if spot.nodeRef.title(spot) != text]
            for node, text in changes:
                undoObj = undo.DataUndo(treeStructure.undoList, node,
                                        skipSame=True)
                if node.setTitle(text):
                    self.nodeModified.emit(node)
                else:
                    treeStructure.undoList.removeLastUndo(undoObj)
        elif self.isChildView and (textList or parent != treeStructure):
            undo.ChildDataUndo(treeStructure.undoList, parent)
            # clear hover to avoid crash if deleted child item was hovered over
            self.treeView.clearHover()
            isDeleting = len(selSpots) > len(textList)
            control = globalref.mainControl.activeControl
            if isDeleting and len(control.windowList) > 1:
                # clear other window selections that are about to be deleted
                for window in control.windowList:
                    if window != control.activeWindow:
                        selectModel = window.treeView.selectionModel()
                        ancestors = set()
                        for spot in selectModel.selectedBranchSpots():
                            ancestors.update(set(spot.spotChain()))
                        if ancestors & set(selSpots):
                            selectModel.selectSpots([], False)
            expandState = self.treeView.savedExpandState(selSpots)
            parent.replaceChildren(textList, treeStructure)
            self.treeView.restoreExpandState(expandState)
            if self.treeView.selectionModel().selectedSpots():
                self.treeView.expandSpot(parentSpot)
            self.treeModified.emit()
        else:
            self.updateContents()  # remove illegal changes

    def selectLineInTree(self):
        """Select the node for the current line in the tree view.
        """
        selSpots = self.treeView.selectionModel().selectedSpots()
        if not selSpots:
            selSpots = [treeStructure.structSpot()]
        spotList = selSpots[0].childSpots()
        cursor = self.textCursor()
        blockStart = cursor.block().position()
        # check for selection all on one line
        if (cursor.selectionStart() >= blockStart and
            cursor.selectionEnd() < blockStart + cursor.block().length()):
            lineNum = cursor.blockNumber()
            if len(spotList) > lineNum:
                self.treeView.selectionModel().selectSpots([spotList[lineNum]],
                                                           True, True)

    def hasSelectedText(self):
        """Return True if text is selected.
        """
        return self.textCursor().hasSelection()

    def highlightSearch(self, wordList=None, regExpList=None):
        """Highlight any found search terms.

        Arguments:
            wordList -- list of words to highlight
            regExpList -- a list of regular expression objects to highlight
        """
        backColor = self.palette().brush(QPalette.ColorGroup.Active,
                                         QPalette.ColorRole.Highlight)
        foreColor = self.palette().brush(QPalette.ColorGroup.Active,
                                         QPalette.ColorRole.HighlightedText)
        if wordList is None:
            wordList = []
        if regExpList is None:
            regExpList = []
        for regExp in regExpList:
            for match in regExp.finditer(self.toPlainText()):
                matchText = match.group()
                if matchText not in wordList:
                    wordList.append(matchText)
        selections = []
        for word in wordList:
            while self.find(word):
                extraSel = QTextEdit.ExtraSelection()
                extraSel.cursor = self.textCursor()
                extraSel.format.setBackground(backColor)
                extraSel.format.setForeground(foreColor)
                selections.append(extraSel)
        cursor = QTextCursor(self.document())
        self.setTextCursor(cursor)  # reset main cursor/selection
        self.setExtraSelections(selections)

    def focusInEvent(self, event):
        """Handle focus-in to put cursor at end for tab-based focus.

        Arguments:
            event -- the focus in event
        """
        if event.reason() in (Qt.FocusReason.TabFocusReason,
                              Qt.FocusReason.BacktabFocusReason):
            self.moveCursor(QTextCursor.MoveOperation.End)
        super().focusInEvent(event)

    def contextMenuEvent(self, event):
        """Override popup menu to remove local undo.

        Arguments:
            event -- the menu event
        """
        menu = self.createStandardContextMenu()
        menu.removeAction(menu.actions()[0])
        menu.removeAction(menu.actions()[0])
        menu.insertSeparator(menu.actions()[0])
        menu.insertAction(menu.actions()[0], self.treeSelectAction)
        self.treeSelectAction.setEnabled(self.isChildView and
                                         len(self.toPlainText().strip()) > 0)
        menu.exec(event.globalPos())

    def keyPressEvent(self, event):
        """Customize handling of return and control keys.

        Ignore return key if not in show children mode and
        emit a signal for app to handle control keys.
        Arguments:
            event -- the key press event
        """
        if (event.modifiers() == Qt.KeyboardModifier.ControlModifier and
            Qt.Key.Key_A <= event.key() <= Qt.Key.Key_Z):
            key = QKeySequence(event.keyCombination())
            self.shortcutEntered.emit(key)
            return
        if self.isChildView or event.key() not in (Qt.Key.Key_Enter,
                                                    Qt.Key.Key_Return):
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Update view if it was collaped by splitter.
        """
        if ((event.oldSize().height() == 0 and event.size().height()) or
            (event.oldSize().width() == 0 and event.size().width())):
            self.updateContents()
        return super().resizeEvent(event)
