#!/usr/bin/env python3

#******************************************************************************
# treemodel.py, provides a class for the tree's data
#
# TreeLine, an information storage program
# Copyright (C) 2025, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import json
from PyQt6.QtCore import (QAbstractItemModel, QMimeData, QModelIndex, Qt,
                          pyqtSignal)
import undo
import treestructure
import globalref


class TreeModel(QAbstractItemModel):
    """Class interfacing between the tree structure and the tree view.
    """
    # first arg is set file modified, second is update trees in other views
    treeModified = pyqtSignal(bool, bool)
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
                node = self.treeStructure.childList[row]
                fakeSpot = list(self.treeStructure.spotRefs)[0]
                spot = node.matchedSpot(fakeSpot)
                return self.createIndex(row, column, spot)
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
            if parentSpot.parentSpot:
                return self.createIndex(parentSpot.row(), 0, parentSpot)
        except AttributeError:
            # attempt to fix an unreproducable bug deleting deep nodes
            pass
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

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Return the output data for the node in the given role.

        Arguments:
            index -- the spot's model index
            role  -- the type of data requested
        """
        spot = index.internalPointer()
        if not spot:
            return None
        node = spot.nodeRef
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return node.title()
        if (role == Qt.ItemDataRole.DecorationRole and
            globalref.genOptions['ShowTreeIcons']):
            return globalref.treeIcons.getIcon(node.formatRef.iconName, True)
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """Set node title after edit operation.

        Return True on success.
        Arguments:
            index -- the node's model index
            value -- the string result of the editing
            role -- the edit role of the data
        """
        if role != Qt.ItemDataRole.EditRole:
            return super().setData(index, value, role)
        node = index.internalPointer().nodeRef
        dataUndo = undo.DataUndo(self.treeStructure.undoList, node)
        if node.setTitle(value):
            self.dataChanged.emit(index, index)
            self.treeModified.emit(True, False)
            return True
        self.treeStructure.undoList.removeLastUndo(dataUndo)
        return False

    def flags(self, index):
        """Return the flags for the node at the given index.

        Arguments:
            index -- the node's model index
        """
        return (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable |
                Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled |
                Qt.ItemFlag.ItemIsDropEnabled)

    def mimeData(self, indexList):
        """Return a mime data object for the given node index branches.

        Arguments:
            indexList -- a list of node indexes to convert
        """
        spots = [index.internalPointer() for index in indexList]
        # remove selections from the same branch
        TreeModel.storedDragSpots = [spot for spot in spots if
                                     spot.parentSpotSet().
                                     isdisjoint(set(spots))]
        nodes = [spot.nodeRef for spot in TreeModel.storedDragSpots]
        TreeModel.storedDragModel = self
        struct = treestructure.TreeStructure(topNodes=nodes, addSpots=False)
        generics = {formatRef.genericType for formatRef in
                    struct.treeFormats.values() if formatRef.genericType}
        for generic in generics:
            genericRef = self.treeStructure.treeFormats[generic]
            struct.treeFormats.addTypeIfMissing(genericRef)
            for formatRef in genericRef.derivedTypes:
                struct.treeFormats.addTypeIfMissing(formatRef)
        data = struct.fileData()
        dataStr = json.dumps(data, indent=0, sort_keys=True)
        mime = QMimeData()
        mime.setData('application/json', bytes(dataStr, encoding='utf-8'))
        return mime

    def mimeTypes(self):
        """Return a list of supported mime types for model objects.
        """
        return ['application/json']

    def supportedDropActions(self):
        """Return drop action enum values that are supported by this model.
        """
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction

    def dropMimeData(self, mimeData, dropAction, row, column, index):
        """Decode mime data and add as a child node to the given index.

        Return True if successful.
        Arguments:
            mimeData -- data for the node branch to be added
            dropAction -- a drop type enum value
            row -- a row number for the drop location
            column -- the column number for the drop location (normally 0)
            index -- the index of the parent node for the drop

        """
        parent = (index.internalPointer().nodeRef if index.internalPointer()
                  else self.treeStructure)
        isMove = (dropAction == Qt.DropAction.MoveAction and
                  TreeModel.storedDragModel == self)
        undoParents = [parent]
        if isMove:
            moveParents = {spot.parentSpot.nodeRef for spot in
                           TreeModel.storedDragSpots}
            undoParents.extend(list(moveParents))
        newStruct = treestructure.structFromMimeData(mimeData)
        # check for valid structure and no circular clone ref and not siblings:
        if newStruct and (not isMove or (not parent.uId in newStruct.nodeDict
                                         and (row >= 0 or {node.uId for node in
                                                           parent.childList}.
                                              isdisjoint({node.uId for node in
                                                      newStruct.childList})))):
            undo.ChildListUndo(self.treeStructure.undoList, undoParents,
                               treeFormats=self.treeStructure.treeFormats)
            if isMove:
                for spot in TreeModel.storedDragSpots:
                    self.treeStructure.deleteNodeSpot(spot)
                newStruct.replaceClonedBranches(self.treeStructure)
            else:
                newStruct.replaceDuplicateIds(self.treeStructure.nodeDict)
            self.treeStructure.addNodesFromStruct(newStruct, parent, row)
            return True
        return False
