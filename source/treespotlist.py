#!/usr/bin/env python3

#******************************************************************************
# treespotlist.py, provides a class to do operations on groups of spots
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import collections
import operator
from PyQt5.QtWidgets import QApplication
import treestructure
import undo


class TreeSpotList(list):
    """Class to do operations on groups of spots.

    Stores a list of nodes.
    """
    def __init__(self, spotList=None, sortSpots=True):
        """Initialize a tree spot group.

        Arguments:
            spotList -- the initial list of spots
            sortSpots -- if True sort the spots in tree order
        """
        super().__init__()
        if spotList:
            self[:] = spotList
            if sortSpots:
                self.sort(key=operator.methodcaller('sortKey'))

    def relatedNodes(self):
        """Return a list of nodes related to these spots.

        Removes any duplicate (cloned) nodes.
        """
        tmpDict = collections.OrderedDict()
        for spot in self:
            node = spot.nodeRef
            tmpDict[node.uId] = node
        return list(tmpDict.values())

    def pasteChild(self, treeStruct, treeView):
        """Paste child nodes from the clipbaord.

        Return True on success.
        Arguments:
            treeStruct -- a ref to the existing tree structure
            treeView -- a ref to the tree view for expanding nodes
        """
        mimeData = QApplication.clipboard().mimeData()
        parentNodes = self.relatedNodes()
        if not parentNodes:
            parentNodes = [treeStruct]
        undoObj = undo.ChildListUndo(treeStruct.undoList, parentNodes,
                                     treeFormats=treeStruct.treeFormats)
        for parent in parentNodes:
            newStruct = treestructure.structFromMimeData(mimeData)
            if not newStruct:
                treeStruct.undoList.removeLastUndo(undoObj)
                return False
            newStruct.replaceDuplicateIds(treeStruct.nodeDict)
            treeStruct.addNodesFromStruct(newStruct, parent)
        for spot in self:
            treeView.expandSpot(spot)
        return True

    def pasteSibling(self, treeStruct, insertBefore=True):
        """Paste a sibling at the these spots.

        Return True on success.
        Arguments:
            treeStruct -- a ref to the existing tree structure
            insertBefore -- if True, insert before these nodes, o/w after
        """
        mimeData = QApplication.clipboard().mimeData()
        parentNodes = [spot.parentSpot.nodeRef for spot in self]
        undoObj = undo.ChildListUndo(treeStruct.undoList, parentNodes,
                                     treeFormats=treeStruct.treeFormats)
        for spot in self:
            newStruct = treestructure.structFromMimeData(mimeData)
            if not newStruct:
                treeStruct.undoList.removeLastUndo(undoObj)
                return False
            newStruct.replaceDuplicateIds(treeStruct.nodeDict)
            parent = spot.parentSpot.nodeRef
            pos = parent.childList.index(spot.nodeRef)
            if not insertBefore:
                pos += 1
            treeStruct.addNodesFromStruct(newStruct, parent, pos)
        return True

    def pasteCloneChild(self, treeStruct, treeView):
        """Paste child clones from the clipbaord.

        Return True on success.
        Arguments:
            treeStruct -- a ref to the existing tree structure
            treeView -- a ref to the tree view for expanding nodes
        """
        mimeData = QApplication.clipboard().mimeData()
        newStruct = treestructure.structFromMimeData(mimeData)
        if not newStruct:
            return False
        try:
            existNodes = [treeStruct.nodeDict[node.uId] for node in
                          newStruct.childList]
        except KeyError:
            return False   # nodes copied from other file
        parentNodes = self.relatedNodes()
        if not parentNodes:
            parentNodes = [treeStruct]
        for parent in parentNodes:
            if not parent.ancestors().isdisjoint(set(existNodes)):
                return False   # circular ref
            for node in existNodes:
                if parent in node.parents():
                    return False   # identical siblings
        undoObj = undo.ChildListUndo(treeStruct.undoList, parentNodes,
                                     treeFormats=treeStruct.treeFormats)
        for parent in parentNodes:
            for node in existNodes:
                parent.childList.append(node)
                node.addSpotRef(parent)
        for spot in self:
            treeView.expandSpot(spot)
        return True

    def pasteCloneSibling(self, treeStruct, insertBefore=True):
        """Paste sibling clones at the these spots.

        Return True on success.
        Arguments:
            treeStruct -- a ref to the existing tree structure
            insertBefore -- if True, insert before these nodes, o/w after
        """
        mimeData = QApplication.clipboard().mimeData()
        newStruct = treestructure.structFromMimeData(mimeData)
        if not newStruct:
            return False
        try:
            existNodes = [treeStruct.nodeDict[node.uId] for node in
                          newStruct.childList]
        except KeyError:
            return False   # nodes copied from other file
        parentNodes = [spot.parentSpot.nodeRef for spot in self]
        for parent in parentNodes:
            if not parent.ancestors().isdisjoint(set(existNodes)):
                return False   # circular ref
            for node in existNodes:
                if parent in node.parents():
                    return False   # identical siblings
        undoObj = undo.ChildListUndo(treeStruct.undoList, parentNodes,
                                     treeFormats=treeStruct.treeFormats)
        for spot in self:
            parent = spot.parentSpot.nodeRef
            pos = parent.childList.index(spot.nodeRef)
            if not insertBefore:
                pos += 1
            for node in existNodes:
                parent.childList.insert(pos, node)
                node.addSpotRef(parent)
        return True

    def addChild(self, treeStruct, treeView):
        """Add new child to these spots.

        Return the new spots.
        Arguments:
            treeStruct -- a ref to the existing tree structure
            treeView -- a ref to the tree view for expanding nodes
        """
        selSpots = self
        if not selSpots:
            selSpots = list(treeStruct.spotRefs)
        undo.ChildListUndo(treeStruct.undoList, [spot.nodeRef for spot in
                                                 selSpots])
        newSpots = []
        for spot in selSpots:
            newNode = spot.nodeRef.addNewChild(treeStruct)
            newSpots.append(newNode.matchedSpot(spot))
            if spot.parentSpot:  # can't expand root struct spot
                treeView.expandSpot(spot)
        return newSpots

    def insertSibling(self, treeStruct, insertBefore=True):
        """Insert a new sibling node at these nodes.

        Return the new spots.
        Arguments:
            treeStruct -- a ref to the existing tree structure
            insertBefore -- if True, insert before these nodes, o/w after
        """
        undo.ChildListUndo(treeStruct.undoList, [spot.parentSpot.nodeRef for
                                                 spot in self])
        newSpots = []
        for spot in self:
            newNode = spot.parentSpot.nodeRef.addNewChild(treeStruct,
                                                          spot.nodeRef,
                                                          insertBefore)
            newSpots.append(newNode.matchedSpot(spot.parentSpot))
        return newSpots

    def delete(self, treeStruct):
        """Delete these spots, return a new spot to select.

        Arguments:
            treeStruct -- a ref to the existing tree structure
        """
        # gather next selected node in decreasing order of desirability
        nextSel = [spot.nextSiblingSpot() for spot in self]
        nextSel.extend([spot.prevSiblingSpot() for spot in self])
        nextSel.extend([spot.parentSpot for spot in self])
        while (not nextSel[0] or not nextSel[0].parentSpot or
               nextSel[0] in self):
            del nextSel[0]
        spotSet = set(self)
        branchSpots = [spot for spot in self if
                       spot.parentSpotSet().isdisjoint(spotSet)]
        undoParents = {spot.parentSpot.nodeRef for spot in branchSpots}
        undo.ChildListUndo(treeStruct.undoList, list(undoParents))
        for spot in branchSpots:
            treeStruct.deleteNodeSpot(spot)
        return nextSel[0]

    def indent(self, treeStruct, treeView):
        """Indent these spots.

        Makes them children of their previous siblings.
        Return the new spots.
        Arguments:
            treeStruct -- a ref to the existing tree structure
            treeView -- a ref to the tree view for expanding nodes
        """
        undoSpots = ([spot.parentSpot for spot in self] +
                     [spot.prevSiblingSpot() for spot in self])
        undo.ChildListUndo(treeStruct.undoList, [spot.nodeRef for spot in
                                                 undoSpots])
        newSpots = []
        expandedList = [treeView.isSpotExpanded(spot) for spot in self]
        for spot in self:
            node = spot.nodeRef
            newParentSpot = spot.prevSiblingSpot()
            node.changeParent(spot.parentSpot, newParentSpot)
            newSpots.append(node.matchedSpot(newParentSpot))
            treeView.expandSpot(newParentSpot)
        for spot, expanded in zip(self, expandedList):
            if expanded:
                treeView.expandSpot(spot)
            else:
                treeView.collapseSpot(spot)
        return newSpots

    def unindent(self, treeStruct):
        """Unindent these spots.

        Makes them their parent's next sibling.
        Return the new spots.
        Arguments:
            treeStruct -- a ref to the existing tree structure
        """
        undoSpots = [spot.parentSpot for spot in self]
        undoSpots.extend([spot.parentSpot for spot in undoSpots])
        undo.ChildListUndo(treeStruct.undoList, [spot.nodeRef for spot in
                                                 undoSpots])
        newSpots = []
        for spot in reversed(self):
            node = spot.nodeRef
            oldParentSpot = spot.parentSpot
            newParentSpot = oldParentSpot.parentSpot
            pos = (newParentSpot.nodeRef.childList.index(oldParentSpot.nodeRef)
                   + 1)
            node.changeParent(oldParentSpot, newParentSpot, pos)
            newSpots.append(node.matchedSpot(newParentSpot))
        return newSpots

    def move(self, treeStruct, up=True):
        """Move these spots up or down by one item.

        Arguments:
            treeStruct -- a ref to the existing tree structure
            up -- if True move up, o/w down
        """
        undo.ChildListUndo(treeStruct.undoList, [spot.parentSpot.nodeRef
                                                 for spot in self])
        if not up:
            self.reverse()
        for spot in self:
            parent = spot.parentSpot.nodeRef
            pos = parent.childList.index(spot.nodeRef)
            del parent.childList[pos]
            pos = pos - 1 if up else pos + 1
            parent.childList.insert(pos, spot.nodeRef)

    def moveToEnd(self, treeStruct, first=True):
        """Move these spots to the first or last position.

        Arguments:
            treeStruct -- a ref to the existing tree structure
            first -- if True move to first position, o/w last
        """
        undo.ChildListUndo(treeStruct.undoList, [spot.parentSpot.nodeRef
                                                 for spot in self])
        if first:
            self.reverse()
        for spot in self:
            parent = spot.parentSpot.nodeRef
            parent.childList.remove(spot.nodeRef)
            if first:
                parent.childList.insert(0, spot.nodeRef)
            else:
                parent.childList.append(spot.nodeRef)
