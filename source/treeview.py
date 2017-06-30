#!/usr/bin/env python3

#******************************************************************************
# treeview.py, provides a class for the indented tree view
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt5.QtCore import QEvent, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QContextMenuEvent, QKeySequence
from PyQt5.QtWidgets import (QAbstractItemView, QHeaderView, QMenu,
                             QStyledItemDelegate, QTreeView)
import treeselection
import treenode
import globalref


class TreeView(QTreeView):
    """Class override for the indented tree view.

    Sets view defaults and links with document for content.
    """
    skippedMouseSelect = pyqtSignal(treenode.TreeNode)
    shortcutEntered = pyqtSignal(QKeySequence)
    def __init__(self, model, allActions, parent=None):
        """Initialize the tree view.

        Arguments:
            model -- the initial model for view data
            allActions -- a dictionary of control actions for popup menus
            parent -- the parent main window
        """
        super().__init__(parent)
        self.resetModel(model)
        self.allActions = allActions
        self.noMouseSelectMode = False
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setHeaderHidden(True)
        self.setItemDelegate(TreeEditDelegate(self))
        self.updateTreeGenOptions()
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(True)
        self.setUniformRowHeights(True)

    def resetModel(self, model):
        """Change the model assigned to this view.

        Also assigns a new selection model.
        Arguments:
            model -- the new model to assign
        """
        self.setModel(model)
        self.setSelectionModel(treeselection.TreeSelection(model, self))

    def updateTreeGenOptions(self):
        """Set the tree to match the current general options.
        """
        if globalref.genOptions['ClickRename']:
            self.setEditTriggers(QAbstractItemView.SelectedClicked)
        else:
            self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        dragAvail = globalref.genOptions['DragTree']
        self.setDragEnabled(dragAvail)
        self.setAcceptDrops(dragAvail)
        self.setIndentation(globalref.genOptions['IndentOffset'] *
                            self.fontInfo().pixelSize())

    def isSpotExpanded(self, spot):
        """Return True if the given spot is expanded (showing children).

        Arguments:
            spot -- the spot to check
        """
        return self.isExpanded(spot.index(self.model()))

    def expandSpot(self, spot):
        """Expand a spot in this view.

        Arguments:
            spot -- the spot to expand
        """
        self.expand(spot.index(self.model()))

    def collapseSpot(self, spot):
        """Collapse a spot in this view.

        Arguments:
            spot -- the spot to collapse
        """
        self.collapse(spot.index(self.model()))

    def expandBranch(self, parentSpot):
        """Expand all spots in the given branch.

        Arguments:
            parentSpot -- the top spot in the branch
        """
        for spot in parentSpot.spotDescendantGen():
            if spot.nodeRef.childList:
                self.expand(spot.index(self.model()))

    def collapseBranch(self, parentSpot):
        """Collapse all spots in the given branch.

        Arguments:
            parentSpot -- the top spot in the branch
        """
        for spot in parentSpot.spotDescendantGen():
            if spot.nodeRef.childList:
                self.collapse(spot.index(self.model()))

    def spotAtTop(self):
        """If view is scrolled, return the spot at the top of the view.

        If not scrolled, return None.
        """
        if self.verticalScrollBar().value() > 0:
            return self.indexAt(QPoint(0, 0)).internalPointer()
        return None

    def scrollToSpot(self, spot):
        """Scroll the view to move the spot to the top position.

        Arguments:
            spot -- the spot to move to the top
        """
        self.scrollTo(spot.index(self.model()),
                      QAbstractItemView.PositionAtTop)

    def endEditing(self):
        """Stop the editing of any item being renamed.
        """
        self.closePersistentEditor(self.selectionModel().currentIndex())

    def contextMenu(self):
        """Return the context menu, creating it if necessary.
        """
        menu = QMenu(self)
        menu.addAction(self.allActions['EditCut'])
        menu.addAction(self.allActions['EditCopy'])
        menu.addAction(self.allActions['EditPaste'])
        menu.addAction(self.allActions['NodeRename'])
        menu.addSeparator()
        menu.addAction(self.allActions['NodeInsertBefore'])
        menu.addAction(self.allActions['NodeInsertAfter'])
        menu.addAction(self.allActions['NodeAddChild'])
        menu.addSeparator()
        menu.addAction(self.allActions['NodeDelete'])
        menu.addAction(self.allActions['NodeIndent'])
        menu.addAction(self.allActions['NodeUnindent'])
        menu.addSeparator()
        menu.addAction(self.allActions['NodeMoveUp'])
        menu.addAction(self.allActions['NodeMoveDown'])
        menu.addSeparator()
        menu.addMenu(self.allActions['DataNodeType'].parent())
        return menu

    def contextMenuEvent(self, event):
        """Show popup context menu on mouse click or menu key.

        Arguments:
            event -- the context menu event
        """
        if event.reason() == QContextMenuEvent.Mouse:
            clickedSpot = self.indexAt(event.pos()).internalPointer()
            if not clickedSpot:
                event.ignore()
                return
            if clickedSpot not in self.selectionModel().selectedSpots():
                self.selectionModel().selectSpot(clickedSpot)
            pos = event.globalPos()
        else:       # shown for menu key or other reason
            selectList = self.selectionModel().selectedSpots()
            if not selectList:
                event.ignore()
                return
            currentSpot = self.selectionModel().currentSpot()
            if currentSpot in selectList:
                selectList.insert(0, currentSpot)
            position = None
            for spot in selectList:
                rect = self.visualRect(spot.index(self.model()))
                pt = QPoint(rect.center().x(), rect.bottom())
                if self.rect().contains(pt):
                    position = pt
                    break
            if not position:
                self.scrollTo(selectList[0].index(self.model()))
                rect = self.visualRect(selectList[0].index(self.model()))
                position = QPoint(rect.center().x(), rect.bottom())
            pos = self.mapToGlobal(position)
        self.contextMenu().popup(pos)
        event.accept()

    def toggleNoMouseSelectMode(self, active=True):
        """Set noMouseSelectMode to active or inactive.

        noMouseSelectMode will not change selection on mouse click,
        it will just signal the clicked node for use in links, etc.
        Arguments:
            active -- if True, activate noMouseSelectMode
        """
        self.noMouseSelectMode = active

    def mousePressEvent(self, event):
        """Skip unselecting click on blank spaces and if in noMouseSelectMode.

        If in noMouseSelectMode, signal which node is under the mouse.
        Arguments:
            event -- the mouse click event
        """
        clickedSpot = self.indexAt(event.pos()).internalPointer()
        if self.noMouseSelectMode and clickedSpot:
            self.skippedMouseSelect.emit(clickedSpot.nodeRef)
            event.ignore()
            return
        super().mousePressEvent(event)

    def dropEvent(self, event):
        """Event handler for view drop actions.

        Selects parent node at destination.
        Arguments:
            event -- the drop event
        """
        clickedSpot = self.indexAt(event.pos()).internalPointer()
        if clickedSpot:
            # clear selection to avoid invalid select bug
            self.selectionModel().selectSpots([], False)
            super().dropEvent(event)
            self.selectionModel().selectSpots([clickedSpot], False)
            self.scheduleDelayedItemsLayout()  # reqd before expand
            self.expandSpot(clickedSpot)
        else:
            super().dropEvent(event)
            self.selectionModel().selectSpots([])
            self.scheduleDelayedItemsLayout()
        self.model().treeModified.emit(True)


class TreeEditDelegate(QStyledItemDelegate):
    """Class override for editing tree items to capture shortcut keys.
    """
    def __init__(self, parent=None):
        """Initialize the delegate class.

        Arguments:
            parent -- the parent view
        """
        super().__init__(parent)

    def createEditor(self, parent, styleOption, modelIndex):
        """Return a new text editor for an item.

        Arguments:
            parent -- the parent widget for the editor
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the item to be edited
        """
        editor = super().createEditor(parent, styleOption, modelIndex)
        return editor

    def eventFilter(self, editor, event):
        """Override to handle shortcut control keys.

        Arguments:
            editor -- the editor that Qt installed a filter on
            event -- the key press event
        """
        if (event.type() == QEvent.KeyPress and
            event.modifiers() == Qt.ControlModifier and
            Qt.Key_A <= event.key() <= Qt.Key_Z):
            key = QKeySequence(event.modifiers() | event.key())
            self.parent().shortcutEntered.emit(key)
            return True
        return super().eventFilter(editor, event)
