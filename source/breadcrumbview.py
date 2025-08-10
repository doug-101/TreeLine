#!/usr/bin/env python3

#******************************************************************************
# breadcrumbview.py, provides a class for the breadcrumb view
#
# TreeLine, an information storage program
# Copyright (C) 2025, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import operator
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPainter, QPalette
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QStyledItemDelegate, QTableWidget,
                             QTableWidgetItem)
import globalref


class CrumbItem(QTableWidgetItem):
    """Class to store breadcrumb item spot refs and positions.
    """
    def __init__(self, spotRef):
        """Initialize the breadcrumb item.

        Arguments:
            spotRef -- ref to the associated spot item
        """
        super().__init__(spotRef.nodeRef.title(spotRef))
        self.spot = spotRef
        self.selectedSpot = False
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setForeground(QApplication.palette().brush(QPalette.
                                                        ColorRole.Link))


class BorderDelegate(QStyledItemDelegate):
    """Class override to show borders between rows.
    """
    def __init__(self, parent=None):
        """Initialize the delegate class.

        Arguments:
            parent -- the parent view
        """
        super().__init__(parent)

    def paint(self, painter, styleOption, modelIndex):
        """Paint the cells with borders between rows.
        """
        super().paint(painter, styleOption, modelIndex)
        cell = self.parent().item(modelIndex.row(), modelIndex.column())
        if modelIndex.row() > 0 and cell:
            upperCell = None
            row = modelIndex.row()
            while not upperCell and row > 0:
                row -= 1
                upperCell = self.parent().item(row, modelIndex.column())
            if cell.text() and upperCell and upperCell.text():
                painter.drawLine(styleOption.rect.topLeft(),
                                 styleOption.rect.topRight())


class BreadcrumbView(QTableWidget):
    """Class override for the breadcrumb view.

    Sets view defaults and updates the content.
    """
    def __init__(self, treeView, parent=None):
        """Initialize the breadcrumb view.

        Arguments:
            treeView - the tree view, needed for the current selection model
            parent -- the parent main window
        """
        super().__init__(parent)
        self.treeView = treeView
        self.borderItems = []
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.
                                     ScrollPerPixel)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setItemDelegate(BorderDelegate(self))
        self.setShowGrid(False)
        self.setMouseTracking(True)
        self.itemClicked.connect(self.changeSelection)

    def updateContents(self):
        """Reload the view's content if the view is shown.

        Avoids update if view is not visible or has zero height or width.
        """
        if not self.isVisible() or self.height() == 0 or self.width() == 0:
            return
        self.clear()
        self.clearSpans()
        selModel = self.treeView.selectionModel()
        selSpots = selModel.selectedSpots()
        if len(selSpots) != 1:
            return
        selSpot = selSpots[0]
        spotList = sorted(list(selSpot.nodeRef.spotRefs),
                          key=operator.methodcaller('sortKey'))
        chainList = [[CrumbItem(chainSpot) for chainSpot in spot.spotChain()]
                     for spot in spotList]
        self.setRowCount(len(chainList))
        for row in range(len(chainList)):
            columns = len(chainList[row]) * 2 - 1
            if columns > self.columnCount():
                self.setColumnCount(columns)
            for col in range(len(chainList[row])):
                item = chainList[row][col]
                if (row == 0 or col >= len(chainList[row - 1]) or
                    item.spot is not chainList[row - 1][col].spot):
                    rowSpan = 1
                    while (row + rowSpan < len(chainList) and
                           col < len(chainList[row + rowSpan]) and
                           item.spot is chainList[row + rowSpan][col].spot):
                        rowSpan += 1
                    if col < len(chainList[row]) - 1:
                        arrowItem = QTableWidgetItem('\u25ba')
                        arrowItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.setItem(row, col * 2 + 1, arrowItem)
                        if rowSpan > 1:
                            self.setSpan(row, col * 2 + 1, rowSpan, 1)
                    self.setItem(row, col * 2, item)
                    if rowSpan > 1:
                        self.setSpan(row, col * 2, rowSpan, 1)
                    if item.spot is selSpot:
                        item.selectedSpot = True
                        item.setForeground(QApplication.palette().
                                           brush(QPalette.ColorRole.
                                                 WindowText))
        self.resizeColumnsToContents()

    def changeSelection(self, item):
        """Change the current selection to given item bassed on a mouse click.

        Arguments:
            item -- the breadcrumb item that was clicked
        """
        selModel = self.treeView.selectionModel()
        if hasattr(item, 'spot') and not item.selectedSpot:
            selModel.selectSpots([item.spot])
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def minimumSizeHint(self):
        """Set a short minimum size fint to allow the display of one row.
        """
        return QSize(super().minimumSizeHint().width(),
                     self.fontInfo().pixelSize() * 3)

    def mouseMoveEvent(self, event):
        """Change the mouse pointer if over a clickable item.

        Arguments:
            event -- the mouse move event
        """
        item = self.itemAt(event.position().toPoint())
        if item and hasattr(item, 'spot') and not item.selectedSpot:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def resizeEvent(self, event):
        """Update view if was collaped by splitter.
        """
        if ((event.oldSize().height() == 0 and event.size().height()) or
            (event.oldSize().width() == 0 and event.size().width())):
            self.updateContents()
        return super().resizeEvent(event)
