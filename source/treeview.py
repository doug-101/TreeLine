#!/usr/bin/env python3

#******************************************************************************
# treeview.py, provides a class for the indented tree view
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re
import unicodedata
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt, pyqtSignal
from PyQt5.QtGui import (QContextMenuEvent, QKeySequence, QMouseEvent,
                         QTextDocument)
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QHeaderView,
                             QLabel, QListWidget, QListWidgetItem, QMenu,
                             QStyledItemDelegate, QTreeView)
import treeselection
import treenode
import miscdialogs
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
        self.incremSearchMode = False
        self.incremSearchString = ''
        self.noMouseSelectMode = False
        self.mouseFocusNoEditMode = False
        self.prevSelSpot = None   # temp, to check for edit at mouse release
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setHeaderHidden(True)
        self.setItemDelegate(TreeEditDelegate(self))
        # use mouse event for editing to avoid with multiple select
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
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

        Collapses parentSpot first to avoid extreme slowness.
        Arguments:
            parentSpot -- the top spot in the branch
        """
        self.collapse(parentSpot.index(self.model()))
        for spot in parentSpot.spotDescendantOnlyGen():
            if spot.nodeRef.childList:
                self.expand(spot.index(self.model()))
        self.expand(parentSpot.index(self.model()))

    def collapseBranch(self, parentSpot):
        """Collapse all spots in the given branch.

        Arguments:
            parentSpot -- the top spot in the branch
        """
        for spot in parentSpot.spotDescendantGen():
            if spot.nodeRef.childList:
                self.collapse(spot.index(self.model()))

    def savedExpandState(self, spots):
        """Return a list of tuples of spots and expanded state (True/False).

        Arguments:
            spots -- an iterable of spots to save
        """
        return [(spot, self.isSpotExpanded(spot)) for spot in spots]

    def restoreExpandState(self, expandState):
        """Expand or collapse based on saved tuples.

        Arguments:
            expandState -- a list of tuples of spots and expanded state
        """
        for spot, expanded in expandState:
            try:
                if expanded:
                    self.expandSpot(spot)
                else:
                    self.collapseSpot(spot)
            except ValueError:
                pass

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

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        """Scroll the view to make node at index visible.

        Overriden to stop autoScroll from horizontally jumping when selecting
        nodes.
        Arguments:
            index -- the node to be made visible
            hint -- where the visible item should be
        """
        horizPos = self.horizontalScrollBar().value()
        super().scrollTo(index, hint)
        self.horizontalScrollBar().setValue(horizPos)

    def endEditing(self):
        """Stop the editing of any item being renamed.
        """
        delegate = self.itemDelegate()
        if delegate.editor:
            delegate.commitData.emit(delegate.editor)
        self.closePersistentEditor(self.selectionModel().currentIndex())

    def incremSearchStart(self):
        """Start an incremental title search.
        """
        self.incremSearchMode = True
        self.incremSearchString = ''
        globalref.mainControl.currentStatusBar().showMessage(_('Search for:'))

    def incremSearchRun(self):
        """Perform an incremental title search.
        """
        msg = _('Search for: {0}').format(self.incremSearchString)
        globalref.mainControl.currentStatusBar().showMessage(msg)
        if (self.incremSearchString and not
            self.selectionModel().selectTitleMatch(self.incremSearchString,
                                                 True, True)):
            msg = _('Search for: {0}  (not found)').format(self.
                                                           incremSearchString)
            globalref.mainControl.currentStatusBar().showMessage(msg)

    def incremSearchNext(self):
        """Go to the next match in an incremental title search.
        """
        if self.incremSearchString:
            if self.selectionModel().selectTitleMatch(self.incremSearchString):
                msg = _('Next: {0}').format(self.incremSearchString)
            else:
                msg = _('Next: {0}  (not found)').format(self.
                                                         incremSearchString)
            globalref.mainControl.currentStatusBar().showMessage(msg)

    def incremSearchPrev(self):
        """Go to the previous match in an incremental title search.
        """
        if self.incremSearchString:
            if self.selectionModel().selectTitleMatch(self.incremSearchString,
                                                      False):
                msg = _('Next: {0}').format(self.incremSearchString)
            else:
                msg = _('Next: {0}  (not found)').format(self.
                                                         incremSearchString)
            globalref.mainControl.currentStatusBar().showMessage(msg)

    def incremSearchStop(self):
        """End an incremental title search.
        """
        self.incremSearchMode = False
        self.incremSearchString = ''
        globalref.mainControl.currentStatusBar().clearMessage()

    def showTypeMenu(self, menu):
        """Show a popup menu for setting the item type.
        """
        index = self.selectionModel().currentIndex()
        self.scrollTo(index)
        rect = self.visualRect(index)
        pt = self.mapToGlobal(QPoint(rect.center().x(), rect.bottom()))
        menu.popup(pt)

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
        menu.addSeparator()
        menu.addAction(self.allActions['ViewExpandBranch'])
        menu.addAction(self.allActions['ViewCollapseBranch'])
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
                self.selectionModel().selectSpots([clickedSpot])
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

    def dropEvent(self, event):
        """Event handler for view drop actions.

        Selects parent node at destination.
        Arguments:
            event -- the drop event
        """
        clickedSpot = self.indexAt(event.pos()).internalPointer()
        # clear selection to avoid invalid multiple selection bug
        self.selectionModel().selectSpots([], False)
        if clickedSpot:
            super().dropEvent(event)
            self.selectionModel().selectSpots([clickedSpot], False)
            self.scheduleDelayedItemsLayout()  # reqd before expand
            self.expandSpot(clickedSpot)
        else:
            super().dropEvent(event)
            self.selectionModel().selectSpots([])
            self.scheduleDelayedItemsLayout()
        if event.isAccepted():
            self.model().treeModified.emit(True, True)

    def toggleNoMouseSelectMode(self, active=True):
        """Set noMouseSelectMode to active or inactive.

        noMouseSelectMode will not change selection on mouse click,
        it will just signal the clicked node for use in links, etc.
        Arguments:
            active -- if True, activate noMouseSelectMode
        """
        self.noMouseSelectMode = active

    def clearHover(self):
        """Post a mouse move event to clear the mouse hover indication.

        Needed to avoid crash when deleting nodes with hovered child nodes.
        """
        event = QMouseEvent(QEvent.MouseMove,
                            QPointF(0.0, self.viewport().width()),
                            Qt.NoButton, Qt.NoButton, Qt.NoModifier)
        QApplication.postEvent(self.viewport(), event)
        QApplication.processEvents()

    def mousePressEvent(self, event):
        """Skip unselecting click if in noMouseSelectMode.

        If in noMouseSelectMode, signal which node is under the mouse.
        Arguments:
            event -- the mouse click event
        """
        if self.incremSearchMode:
            self.incremSearchStop()
        self.prevSelSpot = None
        clickedIndex = self.indexAt(event.pos())
        clickedSpot = clickedIndex.internalPointer()
        selectModel = self.selectionModel()
        if self.noMouseSelectMode:
            if clickedSpot and event.button() == Qt.LeftButton:
                self.skippedMouseSelect.emit(clickedSpot.nodeRef)
            event.ignore()
            return
        if (event.button() == Qt.LeftButton and
            not self.mouseFocusNoEditMode and
            selectModel.selectedCount() == 1 and
            selectModel.currentSpot() == selectModel.selectedSpots()[0] and
            event.pos().x() > self.visualRect(clickedIndex).left() and
            globalref.genOptions['ClickRename']):
            # set for edit if single select and not an expand/collapse click
            self.prevSelSpot = selectModel.selectedSpots()[0]
        self.mouseFocusNoEditMode = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Initiate editing if clicking on a single selected node.

        Arguments:
            event -- the mouse click event
        """
        clickedIndex = self.indexAt(event.pos())
        clickedSpot = clickedIndex.internalPointer()
        if (event.button() == Qt.LeftButton and
            self.prevSelSpot and clickedSpot == self.prevSelSpot):
            self.edit(clickedIndex)
            event.ignore()
            return
        self.prevSelSpot = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Record characters if in incremental search mode.

        Arguments:
            event -- the key event
        """
        if self.incremSearchMode:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
                self.incremSearchStop()
            elif event.key() == Qt.Key_Backspace and self.incremSearchString:
                self.incremSearchString = self.incremSearchString[:-1]
                self.incremSearchRun()
            elif event.text() and unicodedata.category(event.text()) != 'Cc':
                # unicode category excludes control characters
                self.incremSearchString += event.text()
                self.incremSearchRun()
            event.accept()
        elif (event.key() in (Qt.Key_Return, Qt.Key_Enter) and
              not self.itemDelegate().editor):
            # enter key selects current item if not selected
            selectModel = self.selectionModel()
            if selectModel.currentSpot() not in selectModel.selectedSpots():
                selectModel.selectSpots([selectModel.currentSpot()])
                event.accept()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event):
        """Avoid editing a tree item with a get-focus click.

        Arguments:
            event -- the focus in event
        """
        if event.reason() == Qt.MouseFocusReason:
            self.mouseFocusNoEditMode = True
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """Stop incremental search on focus loss.

        Arguments:
            event -- the focus out event
        """
        if self.incremSearchMode:
            self.incremSearchStop()
        super().focusOutEvent(event)


class TreeEditDelegate(QStyledItemDelegate):
    """Class override for editing tree items to capture shortcut keys.
    """
    def __init__(self, parent=None):
        """Initialize the delegate class.

        Arguments:
            parent -- the parent view
        """
        super().__init__(parent)
        self.editor = None

    def createEditor(self, parent, styleOption, modelIndex):
        """Return a new text editor for an item.

        Arguments:
            parent -- the parent widget for the editor
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the item to be edited
        """
        self.editor = super().createEditor(parent, styleOption, modelIndex)
        return self.editor

    def destroyEditor(self, editor, index):
        """Reset editor storage after editing ends.

        Arguments:
            editor -- the editor that is ending
            index -- the index of the edited item
        """
        self.editor = None
        super().destroyEditor(editor, index)

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


class TreeFilterViewItem(QListWidgetItem):
    """Item container for the flat list of filtered nodes.
    """
    def __init__(self, spot, viewParent=None):
        """Initialize the list view item.

        Arguments:
            spot -- the spot to reference for content
            viewParent -- the parent list view
        """
        super().__init__(viewParent)
        self.spot = spot
        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable |
                      Qt.ItemIsEnabled)
        self.update()

    def update(self):
        """Update title and icon from the stored node.
        """
        node = self.spot.nodeRef
        self.setText(node.title())
        if globalref.genOptions['ShowTreeIcons']:
            icon = globalref.treeIcons.getIcon(node.formatRef.iconName, True)
            if icon:
                self.setIcon(icon)


class TreeFilterView(QListWidget):
    """View to show flat list of filtered nodes.
    """
    skippedMouseSelect = pyqtSignal(treenode.TreeNode)
    shortcutEntered = pyqtSignal(QKeySequence)
    def __init__(self, treeViewRef, allActions, parent=None):
        """Initialize the list view.

        Arguments:
            treeViewRef -- a ref to the tree view for data
            allActions -- a dictionary of control actions for popup menus
            parent -- the parent main window
        """
        super().__init__(parent)
        self.structure = treeViewRef.model().treeStructure
        self.selectionModel = treeViewRef.selectionModel()
        self.treeModel = treeViewRef.model()
        self.allActions = allActions
        self.menu = None
        self.noMouseSelectMode = False
        self.mouseFocusNoEditMode = False
        self.prevSelSpot = None   # temp, to check for edit at mouse release
        self.drivingSelectionChange = False
        self.conditionalFilter = None
        self.messageLabel = None
        self.filterWhat = miscdialogs.FindScope.fullData
        self.filterHow = miscdialogs.FindType.keyWords
        self.filterStr = ''
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setItemDelegate(TreeEditDelegate(self))
        # use mouse event for editing to avoid with multiple select
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.itemSelectionChanged.connect(self.updateSelectionModel)
        self.itemChanged.connect(self.changeTitle)
        treeFont = QTextDocument().defaultFont()
        treeFontName = globalref.miscOptions['TreeFont']
        if treeFontName:
            treeFont.fromString(treeFontName)
            self.setFont(treeFont)

    def updateItem(self, node):
        """Update the item corresponding to the given node.

        Arguments:
            node -- the node to be updated
        """
        for row in range(self.count()):
            if self.item(row).spot.nodeRef == node:
                self.blockSignals(True)
                self.item(row).update()
                self.blockSignals(False)
                return

    def updateContents(self):
        """Update filtered contents from current structure and filter criteria.
        """
        if self.conditionalFilter:
            self.conditionalUpdate()
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if self.filterHow == miscdialogs.FindType.regExp:
            criteria = [re.compile(self.filterStr)]
            useRegExpFilter = True
        elif self.filterHow == miscdialogs.FindType.fullWords:
            criteria = []
            for word in self.filterStr.lower().split():
                criteria.append(re.compile(r'(?i)\b{}\b'.
                                           format(re.escape(word))))
            useRegExpFilter = True
        elif self.filterHow == miscdialogs.FindType.keyWords:
            criteria = self.filterStr.lower().split()
            useRegExpFilter = False
        else:         # full phrase
            criteria = [self.filterStr.lower().strip()]
            useRegExpFilter = False
        titlesOnly = self.filterWhat == miscdialogs.FindScope.titlesOnly
        self.blockSignals(True)
        self.clear()
        if useRegExpFilter:
            for rootSpot in self.structure.rootSpots():
                for spot in rootSpot.spotDescendantGen():
                    if spot.nodeRef.regExpSearch(criteria, titlesOnly):
                        item = TreeFilterViewItem(spot, self)
        else:
            for rootSpot in self.structure.rootSpots():
                for spot in rootSpot.spotDescendantGen():
                    if spot.nodeRef.wordSearch(criteria, titlesOnly):
                        item = TreeFilterViewItem(spot, self)
        self.blockSignals(False)
        self.selectItems(self.selectionModel.selectedSpots(), True)
        if self.count() and not self.selectedItems():
            self.item(0).setSelected(True)
        if not self.messageLabel:
            self.messageLabel = QLabel()
            globalref.mainControl.currentStatusBar().addWidget(self.
                                                               messageLabel)
        message = _('Filtering by "{0}", found {1} nodes').format(self.
                                                                  filterStr,
                                                                  self.count())
        self.messageLabel.setText(message)
        QApplication.restoreOverrideCursor()

    def conditionalUpdate(self):
        """Update filtered contents from structure and conditional criteria.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.blockSignals(True)
        self.clear()
        for rootSpot in self.structure.rootSpots():
            for spot in rootSpot.spotDescendantGen():
                if self.conditionalFilter.evaluate(spot.nodeRef):
                    item = TreeFilterViewItem(spot, self)
        self.blockSignals(False)
        self.selectItems(self.selectionModel.selectedSpots(), True)
        if self.count() and not self.selectedItems():
            self.item(0).setSelected(True)
        if not self.messageLabel:
            self.messageLabel = QLabel()
            globalref.mainControl.currentStatusBar().addWidget(self.
                                                               messageLabel)
        message = _('Conditional filtering, found {0} nodes').format(self.
                                                                     count())
        self.messageLabel.setText(message)
        QApplication.restoreOverrideCursor()

    def selectItems(self, spots, signalModel=False):
        """Select items matching given nodes if in filtered view.

        Arguments:
            spots -- the spot list to select
            signalModel -- signal to update the tree selection model if True
        """
        selectSpots = set(spots)
        if not signalModel:
            self.blockSignals(True)
        for item in self.selectedItems():
            item.setSelected(False)
        for row in range(self.count()):
            if self.item(row).spot in selectSpots:
                self.item(row).setSelected(True)
                self.setCurrentItem(self.item(row))
        self.blockSignals(False)

    def updateFromSelectionModel(self):
        """Select items selected in the tree selection model.

        Called from a signal that the tree selection model is changing.
        """
        if self.count() and not self.drivingSelectionChange:
            self.selectItems(self.selectionModel.selectedSpots())

    def updateSelectionModel(self):
        """Change the selection model based on a filter list selection signal.
        """
        self.drivingSelectionChange = True
        self.selectionModel.selectSpots([item.spot for item in
                                         self.selectedItems()])
        self.drivingSelectionChange = False

    def changeTitle(self, item):
        """Update the node title in the model based on an edit signal.

        Reset to the node text if invalid.
        Arguments:
            item -- the filter view item that changed
        """
        if not self.treeModel.setData(item.spot.index(self.treeModel),
                                      item.text()):
            self.blockSignals(True)
            item.setText(item.node.title())
            self.blockSignals(False)

    def nextPrevSpot(self, spot, forward=True):
        """Return the next or previous spot in this filter list view.

        Wraps around ends.  Return None if view doesn't have spot.
        Arguments:
            spot -- the starting spot
            forward -- next if True, previous if False
        """
        for row in range(self.count()):
            if self.item(row).spot == spot:
                if forward:
                    row += 1
                    if row >= self.count():
                        row = 0
                else:
                    row -= 1
                    if row < 0:
                        row = self.count() - 1
                return self.item(row).spot
        return None

    def contextMenu(self):
        """Return the context menu, creating it if necessary.
        """
        if not self.menu:
            self.menu = QMenu(self)
            self.menu.addAction(self.allActions['EditCut'])
            self.menu.addAction(self.allActions['EditCopy'])
            self.menu.addAction(self.allActions['NodeRename'])
            self.menu.addSeparator()
            self.menu.addAction(self.allActions['NodeDelete'])
            self.menu.addSeparator()
            self.menu.addMenu(self.allActions['DataNodeType'].parent())
        return self.menu

    def contextMenuEvent(self, event):
        """Show popup context menu on mouse click or menu key.

        Arguments:
            event -- the context menu event
        """
        if event.reason() == QContextMenuEvent.Mouse:
            clickedItem = self.itemAt(event.pos())
            if not clickedItem:
                event.ignore()
                return
            if clickedItem.spot not in self.selectionModel.selectedSpots():
                self.selectionModel.selectSpots([clickedItem.spot])
            pos = event.globalPos()
        else:       # shown for menu key or other reason
            selectList = self.selectedItems()
            if not selectList:
                event.ignore()
                return
            currentItem = self.currentItem()
            if currentItem in selectList:
                selectList.insert(0, currentItem)
            posList = []
            for item in selectList:
                rect = self.visualItemRect(item)
                pt = QPoint(rect.center().x(), rect.bottom())
                if self.rect().contains(pt):
                    posList.append(pt)
            if not posList:
                self.scrollTo(self.indexFromItem(selectList[0]))
                rect = self.visualItemRect(selectList[0])
                posList = [QPoint(rect.center().x(), rect.bottom())]
            pos = self.mapToGlobal(posList[0])
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
        """Skip unselecting click on blank spaces.

        Arguments:
            event -- the mouse click event
        """
        self.prevSelSpot = None
        clickedItem = self.itemAt(event.pos())
        if not clickedItem:
            event.ignore()
            return
        if self.noMouseSelectMode:
            if event.button() == Qt.LeftButton:
                self.skippedMouseSelect.emit(clickedItem.spot.nodeRef)
            event.ignore()
            return
        if (event.button() == Qt.LeftButton and
            not self.mouseFocusNoEditMode and
            self.selectionModel.selectedCount() == 1 and
            globalref.genOptions['ClickRename']):
            self.prevSelSpot = self.selectionModel.selectedSpots()[0]
        self.mouseFocusNoEditMode = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Initiate editing if clicking on a single selected node.

        Arguments:
            event -- the mouse click event
        """
        clickedItem = self.itemAt(event.pos())
        if (event.button() == Qt.LeftButton and clickedItem and
            self.prevSelSpot and clickedItem.spot == self.prevSelSpot):
            self.editItem(clickedItem)
            event.ignore()
            return
        self.prevSelSpot = None
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event):
        """Avoid editing a tree item with a get-focus click.

        Arguments:
            event -- the focus in event
        """
        if event.reason() == Qt.MouseFocusReason:
            self.mouseFocusNoEditMode = True
        super().focusInEvent(event)
