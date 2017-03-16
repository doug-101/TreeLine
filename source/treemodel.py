#!/usr/bin/env python3

#******************************************************************************
# treemodel.py, provides a class for the tree's data
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt5.QtCore import (QAbstractItemModel, QModelIndex, Qt)
import undo
import globalref


class TreeModel(QAbstractItemModel):
    """Class interfacing between the tree structure and the tree view.
    """
    def __init__(self, treeStructure, parent=None):
        """Initialize a TreeModel.

        Arguments:
            treeStructure -- a ref to the main tree structure
            parent -- optional QObject parent for the model
        """
        super().__init__(parent)
        self.treeStructure = treeStructure

    def index(self, row, column, parentIndex):
        """Returns the index of a spot in the model based on the parent index.

        Uses createIndex() to generate the model indices.
        Arguments:
            row         -- the row of the model node
            column      -- the column (always 0 for now)
            parentIndex -- the parent's model index in the tree structure
        """
        try:
            if not parentIndex.isValid():
                topSpot = self.treeStructure.childList[row].matchedSpot(None)
                return self.createIndex(row, column, topSpot)
            parentSpot = parentIndex.internalPointer()
            node = parentSpot.nodeRef.childList[row]
            return self.createIndex(row, column, node.matchedSpot(parentSpot))
        except IndexError:
            return QModelIndex()

    def parent(self, index):
        """Returns the parent model index of the spot at the given index.

        Arguments:
            index -- the child model index
        """
        try:
            parentSpot = index.internalPointer().parentSpot
            return self.createIndex(parentSpot.row(self), 0, parentSpot)
        except AttributeError:
            return QModelIndex()

    def rowCount(self, parentIndex):
        """Returns the number of children for the spot at the given index.

        Arguments:
            parentIndex -- the parent model index
        """
        try:
            parentSpot = parentIndex.internalPointer()
            return parentSpot.nodeRef.numChildren()
        except AttributeError:
            # top level if no parentIndex
            return len(self.treeStructure.childList)

    def columnCount(self, parentIndex):
        """The number of columns -- always 1 for now.
        """
        return 1

    def data(self, index, role=Qt.DisplayRole):
        """Return the output data for the node in the given role.

        Arguments:
            index -- the spot's model index
            role  -- the type of data requested
        """
        node = index.internalPointer().nodeRef
        if role in (Qt.DisplayRole, Qt.EditRole):
            return node.title()
        if (role == Qt.DecorationRole and
            globalref.genOptions.getValue('ShowTreeIcons')):
            return globalref.treeIcons.getIcon(node.formatRef.iconName, True)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        """Set node title after edit operation.

        Return True on success.
        Arguments:
            index -- the node's model index
            value -- the string result of the editing
            role -- the edit role of the data
        """
        if role != Qt.EditRole:
            return super().setData(index, value, role)
        node = index.internalPointer().nodeRef
        dataUndo = undo.DataUndo(self.treeStructure.undoList, node)
        if node.setTitle(value):
            self.dataChanged.emit(index, index)
            return True
        self.treeStructure.undoList.removeLastUndo(dataUndo)
        return False

    def flags(self, index):
        """Return the flags for the node at the given index.

        Arguments:
            index -- the node's model index
        """
        return (Qt.ItemIsEnabled | Qt.ItemIsSelectable |
                Qt.ItemIsEditable | Qt.ItemIsDragEnabled |
                Qt.ItemIsDropEnabled)
