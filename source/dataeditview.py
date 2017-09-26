#!/usr/bin/env python3

#******************************************************************************
# dataeditview.py, provides a class for the data edit right-hand view
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt5.QtCore import QEvent, QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import (QKeySequence, QPainterPath, QPalette, QPen,
                         QSyntaxHighlighter, QTextCharFormat, QTextCursor,
                         QTextDocument)
from PyQt5.QtWidgets import (QAbstractItemView, QApplication,
                             QStyledItemDelegate, QTableWidget,
                             QTableWidgetItem)
import treenode
import undo
# import urltools
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
            if size.height() > maxHeight:
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
            if hasattr(editor, 'inLinkSelectMode'):
                editor.inLinkSelectMode.connect(self.parent().inLinkSelectMode)
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
            else:
                editor.resetCursor()
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
                # linkRefCollect = cell.node.modelRef.linkRefCollect
                # if (hasattr(editor, 'addedIntLinkFlag') and
                    # (editor.addedIntLinkFlag or
                     # linkRefCollect.linkCount(cell.node, cell.field.name))):
                    # linkRefCollect.searchForLinks(cell.node, cell.field.name)
                    # editor.addedIntLinkFlag = False
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

    def editorEvent(self, event, model, styleOption, modelIndex):
        """Save the mouse click position in order to set the editor's cursor.

        Arguments:
            event -- the mouse click event
            model -- the model (not used)
            styleOption -- the data for styles and geometry  (not used)
            modelIndex -- the index of the cell (not used)
        """
        if event.type() == QEvent.MouseButtonPress:
            self.editorClickPos = event.globalPos()
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
        if event.type() == QEvent.KeyPress:
            view = self.parent()
            if (event.key() == Qt.Key_Tab and
                view.currentRow() == view.rowCount() - 1):
                view.focusOtherView.emit(True)
                return True
            if (event.key() == Qt.Key_Backtab and view.currentRow() == 1):
                view.focusOtherView.emit(False)
                return True
            if (event.modifiers() == Qt.ControlModifier and
                Qt.Key_A <= event.key() <= Qt.Key_Z):
                key = QKeySequence(event.modifiers() | event.key())
                view.shortcutEntered.emit(key)
                return True
        if event.type() == QEvent.MouseButtonPress:
            self.prevNumLines = -1  # reset undo avail for mouse cursor changes
        if event.type() == QEvent.FocusOut:
            self.prevNumLines = -1  # reset undo avail for any focus loss
            if (event.reason() in (Qt.MouseFocusReason,
                                   Qt.TabFocusReason,
                                   Qt.BacktabFocusReason) and
                (not hasattr(editor, 'calendar') or
                 not editor.calendar or not editor.calendar.isVisible()) and
                (not hasattr(editor, 'intLinkDialog') or
                 not editor.intLinkDialog or
                 not editor.intLinkDialog.isVisible())):
                self.parent().setCurrentCell(-1, -1)
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
        self.setAcceptDrops(True)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setItemDelegate(DataEditDelegate(self))
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        pal = self.palette()
        pal.setBrush(QPalette.Base,
                     QApplication.palette().window())
        pal.setBrush(QPalette.Text,
                     QApplication.palette().windowText())
        self.setPalette(pal)
        self.currentItemChanged.connect(self.moveEditor)

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
        for row, field in enumerate(fields, startRow + 1):
            self.setItem(row, 0, self.createInactiveCell(field.name,
                                                         Qt.AlignRight |
                                                         Qt.AlignVCenter))
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
        cell.setFlags(Qt.NoItemFlags)
        if alignment:
            cell.setTextAlignment(alignment)
        return cell

    def moveEditor(self, newCell, prevCell):
        """Close old editor and open new one based on new current cell.

        Arguments:
            newCell -- the new current edit cell item
            prevCell - the old current cell item
        """
        if prevCell and hasattr(prevCell, 'updateText'):
            self.closePersistentEditor(prevCell)
            prevCell.updateText()
            self.resizeRowToContents(prevCell.row())
        if newCell:
            self.openPersistentEditor(newCell)

    def setFont(self, font):
        """Override to avoid setting fonts of inactive cells.

        Arguments:
            font -- the font to set
        """
        global defaultFont
        defaultFont = font

    def highlightSearch(self, wordList=None, regExpList=None):
        """Highlight any found search terms.

        Arguments:
            wordList -- list of words to highlight
            regExpList -- a list of regular expression objects to highlight
        """
        backColor = self.palette().brush(QPalette.Active,
                                         QPalette.Highlight)
        foreColor = self.palette().brush(QPalette.Active,
                                         QPalette.HighlightedText)
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
            cells.extend(self.findItems(word, Qt.MatchFixedString |
                                        Qt.MatchContains))
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
        backColor = self.palette().brush(QPalette.Active,
                                         QPalette.Highlight)
        foreColor = self.palette().brush(QPalette.Active,
                                         QPalette.HighlightedText)
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
        if event.reason() == Qt.TabFocusReason:
            for row in range(self.rowCount()):
                cell = self.item(row, 1)
                if hasattr(cell, 'doc'):
                    self.setCurrentItem(cell)
                    break
        elif event.reason() == Qt.BacktabFocusReason:
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
        cell = self.itemAt(event.pos())
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
        cell = self.itemAt(event.pos())
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
        if (event.button() == Qt.LeftButton and
            event.modifiers() == Qt.ControlModifier):
            cell = self.itemAt(event.pos())
            if cell and isinstance(cell, DataEditCell):
                xOffest = (event.pos().x() -
                           self.columnViewportPosition(cell.column()))
                yOffset = (event.pos().y() -
                           self.rowViewportPosition(cell.row()))
                pt = QPointF(xOffest, yOffset)
                pos = cell.doc.documentLayout().hitTest(pt, Qt.ExactHit)
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
            searchText -- the text to find in a non-regexp search
            regExpObj -- the regular expression to find if searchText is blank
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
            if self.searchText:
                pos = text.lower().find(self.searchText, pos)
                matchLen = len(self.searchText)
            else:
                match = self.regExpObj.search(text, pos)
                pos = match.start() if match else -1
                matchLen = len(match.group())
        if pos >= 0:
            self.setFormat(pos, matchLen, self.charFormat)
