#!/usr/bin/env python3

#******************************************************************************
# dataeditview.py, provides a class for the data edit right-hand view
#
# TreeLine, an information storage program
# Copyright (C) 2025, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (QKeySequence, QPainterPath, QPalette, QPen,
                         QSyntaxHighlighter, QTextCharFormat, QTextCursor,
                         QTextDocument)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QStyledItemDelegate, QTableWidget,
                             QTableWidgetItem)
import treenode
import undo
import urltools
import dataeditors
import globalref

_minColumnWidth = 80
defaultFont = None

class DataEditCell(QTableWidgetItem):
    """Class override for data edit view cells.
    Used for the cells with editable content.
    """
    def __init__(self, spot, field, titleCellRef, typeCellRef):
        """Initialize the editable cells in the data edit view.

        Arguments:
            spot -- the spot referenced by this cell
            field -- the field object referenced by this cell
            titleCellRef -- the title cell to update based on data changes
            typeCellRef -- the format type cell to update based on type changes
        """
        super().__init__()
        self.spot = spot
        self.node = spot.nodeRef
        self.field = field
        self.titleCellRef = titleCellRef
        self.typeCellRef = typeCellRef
        self.errorFlag = False
        self.cursorPos = (-1, -1)
        self.scrollPos = -1
        # store doc to speed up delegate sizeHint and paint calls
        self.doc = QTextDocument()
        self.doc.setDefaultFont(defaultFont)
        self.doc.setDocumentMargin(6)
        self.updateText()

    def updateText(self):
        """Update the text based on the current node data.
        """
        self.errorFlag = False
        try:
            self.setText(self.field.editorText(self.node))
        except ValueError as err:
            if len(err.args) >= 2:
                self.setText(err.args[1])
            else:
                self.setText(self.node.data.get(self.field.name, ''))
            self.errorFlag = True
        if self.field.showRichTextInCell:
            self.doc.setHtml(self.text())
        else:
            self.doc.setPlainText(self.text())

    def storeEditorState(self, editor):
        """Store the cursor & scroll positions baseed on an editor signal.

        Arguments:
            editor -- the editor that will get its state saved
        """
        self.cursorPos = editor.cursorPosTuple()
        self.scrollPos = editor.scrollPosition()


class DataEditDelegate(QStyledItemDelegate):
    """Class override for display and editing of DataEditCells.
    """
    def __init__(self, parent=None):
        """Initialize the delegate class.

        Arguments:
            parent -- the parent view
        """
        super().__init__(parent)
        self.editorClickPos = None
        self.tallEditScrollPos = -1
        self.lastEditor = None
        self.prevNumLines = -1

    def paint(self, painter, styleOption, modelIndex):
        """Paint the Data Edit Cells with support for rich text.

        Other cells are painted with the base class default.
        Also paints an error rectangle if the format error flag is set.
        Arguments:
            painter -- the painter instance
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the cell to be painted
        """
        cell = self.parent().item(modelIndex.row(), modelIndex.column())
        if isinstance(cell, DataEditCell):
            painter.save()
            doc = cell.doc
            doc.setTextWidth(styleOption.rect.width())
            painter.translate(styleOption.rect.topLeft())
            paintRect = QRectF(0, 0, styleOption.rect.width(),
                               styleOption.rect.height())
            painter.setClipRect(paintRect)
            painter.fillRect(paintRect, QApplication.palette().base())
            painter.setPen(QPen(QApplication.palette().text(), 1))
            painter.drawRect(paintRect.adjusted(0, 0, -1, -1))
            doc.drawContents(painter)
            if cell.errorFlag:
                path = QPainterPath(QPointF(0, 0))
                path.lineTo(0, 10)
                path.lineTo(10, 0)
                path.closeSubpath()
                painter.fillPath(path, QApplication.palette().highlight())
            painter.restore()
        else:
            super().paint(painter, styleOption, modelIndex)

    def sizeHint(self, styleOption, modelIndex):
        """Return the size of Data Edit Cells with rich text.

        Other cells return the base class size.
        Arguments:
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the cell to be painted
        """
        cell = self.parent().item(modelIndex.row(), modelIndex.column())
        if isinstance(cell, DataEditCell):
            doc = cell.doc
            doc.setTextWidth(styleOption.rect.width())
            size = doc.documentLayout().documentSize().toSize()
            maxHeight = self.parent().height() * 9 // 10  # 90% of view height
            if (size.height() > maxHeight and
                globalref.genOptions['EditorLimitHeight']):
                size.setHeight(maxHeight)
            if cell.field.numLines > 1:
                minDoc = QTextDocument('\n' * (cell.field.numLines - 1))
                minDoc.setDefaultFont(cell.doc.defaultFont())
                minHeight = (minDoc.documentLayout().documentSize().toSize().
                             height())
                if minHeight > size.height():
                    size.setHeight(minHeight)
            return size + QSize(0, 4)
        return super().sizeHint(styleOption, modelIndex)

    def createEditor(self, parent, styleOption, modelIndex):
        """Return a new text editor for a cell.

        Arguments:
            parent -- the parent widget for the editor
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the cell to be edited
        """
        cell = self.parent().item(modelIndex.row(), modelIndex.column())
        if isinstance(cell, DataEditCell):
            editor = getattr(dataeditors, cell.field.editorClassName)(parent)
            editor.setFont(cell.doc.defaultFont())
            if hasattr(editor, 'fieldRef'):
                editor.fieldRef = cell.field
            if hasattr(editor, 'nodeRef'):
                editor.nodeRef = cell.node
            if cell.errorFlag:
                editor.setErrorFlag()
            # self.parent().setFocusProxy(editor)
            editor.contentsChanged.connect(self.commitData)
            editor.editEnding.connect(cell.storeEditorState)
            if (not globalref.genOptions['EditorLimitHeight'] and
                hasattr(editor, 'keyPressed')):
                editor.keyPressed.connect(self.scrollOnKeyPress)
            if hasattr(editor, 'inLinkSelectMode'):
                editor.inLinkSelectMode.connect(self.parent().
                                                changeInLinkSelectMode)
            if hasattr(editor, 'setLinkFromNode'):
                self.parent().internalLinkSelected.connect(editor.
                                                           setLinkFromNode)
            # viewport filter required to catch editor events
            try:
                editor.viewport().installEventFilter(self)
            except AttributeError:
                try:
                    editor.lineEdit().installEventFilter(self)
                except AttributeError:
                    pass
            self.lastEditor = editor
            editor.setFocus()
            return editor
        return super().createEditor(parent, styleOption, modelIndex)

    def setEditorData(self, editor, modelIndex):
        """Sets the text to be edited by the editor item.

        Arguments:
            editor -- the editor widget
            modelIndex -- the index of the cell to being edited
        """
        cell = self.parent().item(modelIndex.row(), modelIndex.column())
        if isinstance(cell, DataEditCell):
            try:
                # set from data to pick up any background changes
                editor.setContents(cell.field.editorText(cell.node))
            except ValueError:
                # if data bad, just set it like the cell
                editor.setContents(modelIndex.data())
            if cell.errorFlag:
                editor.setErrorFlag()
            editor.show()
            if self.editorClickPos:
                editor.setCursorPoint(self.editorClickPos)
                self.editorClickPos = None
            elif globalref.genOptions['EditorLimitHeight']:
                if cell.cursorPos[1] >= 0:
                    editor.setCursorPos(*cell.cursorPos)
                    cell.cursorPos = (-1, -1)
                    if cell.scrollPos >= 0:
                        editor.setScrollPosition(cell.scrollPos)
                        cell.scrollPos = -1
                else:
                    editor.resetCursor()
            if (not globalref.genOptions['EditorLimitHeight'] and
                globalref.genOptions['EditorOnHover'] and
                self.tallEditScrollPos >= 0):
                # maintain scroll position for unlimited height editors
                # when hovering (use adjustScroll() for non-hovering
                self.parent().verticalScrollBar().setValue(self.
                                                           tallEditScrollPos)
        else:
            super().setEditorData(editor, modelIndex)

    def setModelData(self, editor, styleOption, modelIndex):
        """Update the model with the results from an editor.

        Sets the cell error flag if the format doesn't match.
        Arguments:
            editor -- the editor widget
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the cell to be painted
        """
        cell = self.parent().item(modelIndex.row(), modelIndex.column())
        if isinstance(cell, DataEditCell):
            if editor.modified:
                newText = editor.contents()
                numLines = newText.count('\n')
                skipUndoAvail = numLines == self.prevNumLines
                self.prevNumLines = numLines
                treeStructure = globalref.mainControl.activeControl.structure
                undo.DataUndo(treeStructure.undoList, cell.node, False, False,
                              skipUndoAvail, cell.field.name)
                try:
                    cell.node.setData(cell.field, newText)
                except ValueError:
                    editor.setErrorFlag()
                self.parent().nodeModified.emit(cell.node)
                cell.titleCellRef.setText(cell.node.title(cell.spot))
                cell.typeCellRef.setText(cell.node.formatRef.name)
                editor.modified = False
        else:
            super().setModelData(editor, styleOption, modelIndex)

    def updateEditorGeometry(self, editor, styleOption, modelIndex):
        """Update the editor geometry to match the cell.

        Arguments:
            editor -- the editor widget
            styleOption -- the data for styles and geometry
            modelIndex -- the index of the cell to be painted
        """
        editor.setMaximumSize(self.sizeHint(styleOption, modelIndex))
        super().updateEditorGeometry(editor, styleOption, modelIndex)

    def adjustScroll(self):
        """Reset the scroll back to the original for unlimited height editors.

        Called from signal after any scroll change.
        Needed for non-hovering to fix late scroll reset after editor created.
        """
        if (not globalref.genOptions['EditorLimitHeight'] and
            not globalref.genOptions['EditorOnHover'] and
            self.tallEditScrollPos >= 0):
            self.parent().verticalScrollBar().setValue(self.tallEditScrollPos)
            self.tallEditScrollPos = -1

    def scrollOnKeyPress(self, editor):
        """Adjust the scroll position to make cursor visible.

        Needed after key presses on unlimited height editors.
        Arguments:
            editor -- the editor with the key press
        """
        if not globalref.genOptions['EditorLimitHeight']:
            view = self.parent()
            cursorRect = editor.cursorRect()
            upperPos = editor.mapToGlobal(cursorRect.topLeft()).y()
            lowerPos = editor.mapToGlobal(cursorRect.bottomLeft()).y()
            viewRect = view.viewport().rect()
            viewTop = view.mapToGlobal(viewRect.topLeft()).y()
            viewBottom = view.mapToGlobal(viewRect.bottomLeft()).y()
            bar = view.verticalScrollBar()
            if upperPos < viewTop:
                bar.setValue(bar.value() - (viewTop - upperPos))
            elif lowerPos > viewBottom:
                bar.setValue(bar.value() + (lowerPos - viewBottom))

    def editorEvent(self, event, model, styleOption, modelIndex):
        """Save the mouse click position in order to set the editor's cursor.

        Arguments:
            event -- the mouse click event
            model -- the model (not used)
            styleOption -- the data for styles and geometry  (not used)
            modelIndex -- the index of the cell (not used)
        """
        if event.type() == QEvent.Type.MouseButtonPress:
            self.editorClickPos = event.globalPosition().toPoint()
            # save scroll position for clicks on unlimited height editors
            self.tallEditScrollPos = self.parent().verticalScrollBar().value()
        return super().editorEvent(event, model, styleOption, modelIndex)

    def eventFilter(self, editor, event):
        """Override to handle various focus changes and control keys.

        Navigate away from this view if tab hit on end items.
        Catches tab before QDelegate's event filter on the editor.
        Also closes the editor if focus is lost for certain reasons.
        Arguments:
            editor -- the editor that Qt installed a filter on
            event -- the key press event
        """
        if event.type() == QEvent.Type.KeyPress:
            view = self.parent()
            if (event.key() == Qt.Key.Key_Tab and
                view.currentRow() == view.rowCount() - 1):
                view.focusOtherView.emit(True)
                return True
            if (event.key() == Qt.Key.Key_Backtab and view.currentRow() == 1):
                view.focusOtherView.emit(False)
                return True
            if (event.modifiers() == Qt.KeyboardModifier.ControlModifier and
                Qt.Key.Key_A <= event.key() <= Qt.Key.Key_Z):
                key = QKeySequence(event.keyCombination())
                view.shortcutEntered.emit(key)
                return True
        if event.type() == QEvent.Type.MouseButtonPress:
            self.prevNumLines = -1  # reset undo avail for mouse cursor changes
        if event.type() == QEvent.Type.FocusOut:
            self.prevNumLines = -1  # reset undo avail for any focus loss
            if (event.reason() in (Qt.FocusReason.MouseFocusReason,
                                   Qt.FocusReason.TabFocusReason,
                                   Qt.FocusReason.BacktabFocusReason)
                and (not hasattr(editor, 'calendar') or
                not editor.calendar or not editor.calendar.isVisible()) and
                (not hasattr(editor, 'intLinkDialog') or
                 not editor.intLinkDialog or
                 not editor.intLinkDialog.isVisible())):
                self.parent().endEditor()
                return True
        return super().eventFilter(editor, event)


class DataEditView(QTableWidget):
    """Class override for the table-based data edit view.
    
    Sets view defaults and updates the content.
    """
    nodeModified = pyqtSignal(treenode.TreeNode)
    inLinkSelectMode = pyqtSignal(bool)
    internalLinkSelected = pyqtSignal(treenode.TreeNode)
    focusOtherView = pyqtSignal(bool)
    hoverFocusActive = pyqtSignal()
    shortcutEntered = pyqtSignal(QKeySequence)
    def __init__(self, treeView, allActions, isChildView=True,
                 parent=None):
        """Initialize the data edit view default view settings.

        Arguments:
            treeView - the tree view, needed for the current selection model
            allActions -- a dict containing actions for the editor context menu
            isChildView -- shows selected nodes if false, child nodes if true
            parent -- the parent main window
        """
        super().__init__(0, 2, parent)
        self.treeView = treeView
        self.allActions = allActions
        self.isChildView = isChildView
        self.hideChildView = not globalref.genOptions['InitShowChildPane']
        self.prevHoverCell = None
        self.inLinkSelectActive = False
        self.setAcceptDrops(True)
        self.setMouseTracking(globalref.genOptions['EditorOnHover'])
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.
                                     ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(self.fontMetrics().
                                               lineSpacing())
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setItemDelegate(DataEditDelegate(self))
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        pal = self.palette()
        pal.setBrush(QPalette.ColorRole.Base,
                     QApplication.palette().window())
        pal.setBrush(QPalette.ColorRole.Text,
                     QApplication.palette().windowText())
        self.setPalette(pal)
        self.currentItemChanged.connect(self.moveEditor)
        self.verticalScrollBar().valueChanged.connect(self.itemDelegate().
                                                      adjustScroll)

    def updateContents(self):
        """Reload the view's content if the view is shown.

        Avoids update if view is not visible or has zero height or width.
        """
        selSpots = self.treeView.selectionModel().selectedSpots()
        if self.isChildView:
            if (len(selSpots) > 1 or self.hideChildView or
                (selSpots and not selSpots[0].nodeRef.childList)):
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
        self.clear()
        if selSpots:
            self.hide() # 2nd update very slow if shown during update
            self.setRowCount(100000)
            rowNum = -2
            for spot in selSpots:
                rowNum = self.addNodeData(spot, rowNum + 2)
            self.setRowCount(rowNum + 1)
            self.adjustSizes()
            self.scrollToTop()
            self.show()

    def addNodeData(self, spot, startRow):
        """Populate the view with the data from the given node.

        Returns the last row number used.
        Arguments:
            spot -- the spot to add
            startRow -- the row offset
        """
        node = spot.nodeRef
        formatName = node.formatRef.name
        typeCell = self.createInactiveCell(formatName)
        self.setItem(startRow, 0, typeCell)
        titleCell = self.createInactiveCell(node.title(spot))
        self.setItem(startRow, 1, titleCell)
        fields = node.formatRef.fields()
        if not globalref.genOptions['EditNumbering']:
            fields = [field for field in fields
                      if field.typeName != 'Numbering']
        if not globalref.genOptions['ShowMath']:
            fields = [field for field in fields
                      if field.typeName != 'Math']
        row = 0  # initialize for cases with only Numbering or Math fields
        for row, field in enumerate(fields, startRow + 1):
            self.setItem(row, 0, self.createInactiveCell(field.name,
                                                         Qt.AlignmentFlag.AlignRight |
                                                         Qt.AlignmentFlag.AlignVCenter))
            self.setItem(row, 1, DataEditCell(spot, field, titleCell,
                                              typeCell))
        self.setItem(row + 1, 0, self.createInactiveCell(''))
        self.setItem(row + 1, 1, self.createInactiveCell(''))
        return row

    def updateUnselectedCells(self):
        """Refresh the data in active cells, keeping the cell structure.
        """
        if not self.isVisible() or self.height() == 0 or self.width() == 0:
            return
        selSpots = self.treeView.selectionModel().selectedSpots()
        if self.isChildView:
            if not selSpots:
                # use top node childList from tree structure
                selSpots = [globalref.mainControl.activeControl.structure.
                            structSpot()]
            selSpots = selSpots[0].childSpots()
        elif not selSpots:
            return
        rowNum = -2
        for spot in selSpots:
            rowNum = self.refreshNodeData(spot, rowNum + 2)

    def refreshNodeData(self, spot, startRow):
        """Refresh the data in active cells for this node.

        Returns the last row number used.
        Arguments:
            node -- the node to add
            startRow -- the row offset
        """
        node = spot.nodeRef
        self.item(startRow, 1).setText(node.title(spot))
        fields = node.formatRef.fields()
        if not globalref.genOptions['EditNumbering']:
            fields = [field for field in fields
                      if field.typeName != 'Numbering']
        if not globalref.genOptions['ShowMath']:
            fields = [field for field in fields
                      if field.typeName != 'Math']
        for row, field in enumerate(fields, startRow + 1):
            cell = self.item(row, 1)
            if not cell.isSelected():
                cell.updateText()
        return row

    @staticmethod
    def createInactiveCell(text, alignment=None):
        """Return a new inactive data edit view cell.

        Arguments:
            text -- the initial text string for the cell
            alignment -- the text alignment QT constant (None for default)
        """
        cell = QTableWidgetItem(text)
        cell.setFlags(Qt.ItemFlag.NoItemFlags)
        if alignment:
            cell.setTextAlignment(alignment)
        return cell

    def moveEditor(self, newCell, prevCell):
        """Close old editor and open new one based on new current cell.

        Arguments:
            newCell -- the new current edit cell item
            prevCell - the old current cell item
        """
        try:
            if prevCell and hasattr(prevCell, 'updateText'):
                self.closePersistentEditor(prevCell)
                prevCell.updateText()
                self.resizeRowToContents(prevCell.row())
        except RuntimeError:
            pass   # avoid non-repeatable error involving deleted c++ object
        if newCell:
            self.openPersistentEditor(newCell)

    def endEditor(self):
        """End persistent editors by changing active cells.
        """
        self.setCurrentCell(-1, -1)

    def setFont(self, font):
        """Override to avoid setting fonts of inactive cells.

        Arguments:
            font -- the font to set
        """
        global defaultFont
        defaultFont = font

    def changeInLinkSelectMode(self, active=True):
        """Change the internal link select mode.

        Changes the internal variable (controlling hover) and signals the tree.
        Arguments:
            active -- if True, starts the mode, o/w ends
        """
        self.inLinkSelectActive = active
        self.inLinkSelectMode.emit(active)

    def updateInLinkSelectMode(self, active=True):
        """Update the internal link select mode.

        Updates the internal variable (controlling hover).
        Arguments:
            active -- if True, starts the mode, o/w ends
        """
        self.inLinkSelectActive = active

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
        charFormat = QTextCharFormat()
        charFormat.setBackground(backColor)
        charFormat.setForeground(foreColor)
        spot = self.treeView.selectionModel().selectedSpots()[0]
        if wordList is None:
            wordList = []
        if regExpList is None:
            regExpList = []
        for regExp in regExpList:
            for match in regExp.finditer('\n'.join(spot.nodeRef.
                                                   output(spotRef=spot))):
                matchText = match.group().lower()
                if matchText not in wordList:
                    wordList.append(matchText)
        cells = []
        completedCells = []
        for word in wordList:
            cells.extend(self.findItems(word, Qt.MatchFlag.MatchFixedString |
                                        Qt.MatchFlag.MatchContains))
        for cell in cells:
            if hasattr(cell, 'doc') and cell not in completedCells:
                highlighter = SearchHighlighter(wordList, charFormat, cell.doc)
                completedCells.append(cell)

    def highlightMatch(self, searchText='', regExpObj=None, cellNum=0,
                       skipMatches=0):
        """Highlight a specific search result.

        Arguments:
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
            cellNum -- the vertical position (field number) of the cell
            skipMatches -- number of previous matches to skip in this field
        """
        backColor = self.palette().brush(QPalette.ColorGroup.Active,
                                         QPalette.ColorRole.Highlight)
        foreColor = self.palette().brush(QPalette.ColorGroup.Active,
                                         QPalette.ColorRole.HighlightedText)
        charFormat = QTextCharFormat()
        charFormat.setBackground(backColor)
        charFormat.setForeground(foreColor)
        cellNum += 1    # skip title line
        cell = self.item(cellNum, 1)
        highlighter = MatchHighlighter(cell.doc, charFormat, searchText,
                                       regExpObj, skipMatches)

    def adjustSizes(self):
        """Update the column widths and row heights.
        """
        self.resizeColumnToContents(0)
        if self.columnWidth(0) < _minColumnWidth:
            self.setColumnWidth(0, _minColumnWidth)
        self.setColumnWidth(1, max(self.width() - self.columnWidth(0) -
                                   self.verticalScrollBar().width() - 5,
                                   _minColumnWidth))
        self.resizeRowsToContents()

    def focusInEvent(self, event):
        """Handle focus-in to start an editor when tab is used.

        Arguments:
            event -- the focus in event
        """
        if event.reason() == Qt.FocusReason.TabFocusReason:
            for row in range(self.rowCount()):
                cell = self.item(row, 1)
                if hasattr(cell, 'doc'):
                    self.setCurrentItem(cell)
                    break
        elif event.reason() == Qt.FocusReason.BacktabFocusReason:
            for row in range(self.rowCount() - 1, -1, -1):
                cell = self.item(row, 1)
                if hasattr(cell, 'doc'):
                    self.setCurrentItem(cell)
                    break
        super().focusInEvent(event)

    def resizeEvent(self, event):
        """Update view if was collaped by splitter.
        """
        if ((event.oldSize().height() == 0 and event.size().height()) or
            (event.oldSize().width() == 0 and event.size().width())):
            self.updateContents()
        self.adjustSizes()
        return super().resizeEvent(event)

    def dragEnterEvent(self, event):
        """Accept drags of files to this window.
        
        Arguments:
            event -- the drag event object
        """
        if event.mimeData().hasUrls():
            event.accept()

    def dragMoveEvent(self, event):
        """Accept drags of files to this window.
        
        Arguments:
            event -- the drag event object
        """
        cell = self.itemAt(event.position().toPoint())
        if (isinstance(cell, DataEditCell) and
            getattr(dataeditors, cell.field.editorClassName).dragLinkEnabled):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Open a file dropped onto this window.
        
         Arguments:
             event -- the drop event object
        """
        cell = self.itemAt(event.position().toPoint())
        fileList = event.mimeData().urls()
        if fileList and isinstance(cell, DataEditCell):
            self.setCurrentItem(cell)
            self.setFocus()
            self.itemDelegate().lastEditor.addDroppedUrl(fileList[0].
                                                         toLocalFile())

    def mousePressEvent(self, event):
        """Handle ctrl + click to follow links.

        Arguments:
            event -- the mouse event
        """
        if (event.button() == Qt.MouseButton.LeftButton and
            event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            cell = self.itemAt(event.position().toPoint())
            if cell and isinstance(cell, DataEditCell):
                xOffest = (event.position().toPoint().x() -
                           self.columnViewportPosition(cell.column()))
                yOffset = (event.position().toPoint().y() -
                           self.rowViewportPosition(cell.row()))
                pt = QPointF(xOffest, yOffset)
                pos = cell.doc.documentLayout().hitTest(pt, Qt.HitTestAccuracy.ExactHit)
                if pos >= 0:
                    cursor = QTextCursor(cell.doc)
                    cursor.setPosition(pos)
                    address = cursor.charFormat().anchorHref()
                    if address:
                        if address.startswith('#'):
                            (self.treeView.selectionModel().
                             selectNodeById(address[1:]))
                        else:     # check for relative path
                            if urltools.isRelative(address):
                                defaultPath = (globalref.mainControl.
                                               defaultPathObj(True))
                                address = urltools.toAbsolute(address,
                                                              str(defaultPath))
                            dataeditors.openExtUrl(address)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move event to create editors on hover.

        Arguments:
            event -- the mouse event
        """
        cell = self.itemAt(event.position().toPoint())
        if cell and hasattr(cell, 'doc'):
            oldCell = self.currentItem()
            if (cell != oldCell and cell != self.prevHoverCell and
                not self.inLinkSelectActive):
                # save scroll position for unlimited height editors
                self.itemDelegate().tallEditScrollPos = (self.
                                                         verticalScrollBar().
                                                         value())
                self.prevHoverCell = cell
                self.hoverFocusActive.emit()
                self.setFocus()
                if oldCell and hasattr(oldCell, 'doc'):
                    # these lines result in two calls to moveEditor, but seems
                    # to be necessary to avoid race that leaves stray editors
                    self.moveEditor(None, oldCell)
                    self.setCurrentItem(None)
                try:
                    self.setCurrentItem(cell)
                except RuntimeError:
                    # catch error if view updates due to node rename ending
                    pass
        else:
            self.prevHoverCell = None


class SearchHighlighter(QSyntaxHighlighter):
    """Class override to highlight search terms in cell text.

    Used to highlight search words from a list.
    """
    def __init__(self, wordList, charFormat, doc):
        """Initialize the highlighter with the text document.

        Arguments:
            wordList -- list of search terms
            charFormat -- the formatting to apply
            doc -- the text document
        """
        super().__init__(doc)
        self.wordList = wordList
        self.charFormat = charFormat

    def highlightBlock(self, text):
        """Override method to highlight search terms in block of text.

        Arguments:
            text -- the text to highlight
        """
        for word in self.wordList:
            pos = text.lower().find(word, 0)
            while pos >= 0:
                self.setFormat(pos, len(word), self.charFormat)
                pos = text.lower().find(word, pos + len(word))


class MatchHighlighter(QSyntaxHighlighter):
    """Class override to highlight a specific search result in cell text.

    Used to highlight a text or reg exp match.
    """
    def __init__(self, doc, charFormat, searchText='', regExpObj=None,
                 skipMatches=0):
        """Initialize the highlighter with the text document.

        Arguments:
            doc -- the text document
            charFormat -- the formatting to apply
            searchText -- the text to find if no regexp is given
            regExpObj -- the regular expression to find if given
            skipMatches -- number of previous matches to skip
        """
        super().__init__(doc)
        self.charFormat = charFormat
        self.searchText = searchText
        self.regExpObj = regExpObj
        self.skipMatches = skipMatches

    def highlightBlock(self, text):
        """Override method to highlight a match in block of text.

        Arguments:
            text -- the text to highlight
        """
        pos = matchLen = 0
        for matchNum in range(self.skipMatches + 1):
            pos += matchLen
            if self.regExpObj:
                match = self.regExpObj.search(text, pos)
                pos = match.start() if match else -1
                matchLen = len(match.group()) if match else 0
            else:
                pos = text.lower().find(self.searchText, pos)
                matchLen = len(self.searchText)
        if pos >= 0:
            self.setFormat(pos, matchLen, self.charFormat)
