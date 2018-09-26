#!/usr/bin/env python3

#******************************************************************************
# treespot.py, provides a class to store locations of tree node instances
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import sys
import operator


class TreeSpot:
    """Class to store location info for tree node instances.

    Used to generate breadcrumb navigation and interface with tree views.
    A spot without a parent spot is an imaginary root spot, wihout a real node.
    """
    def __init__(self, nodeRef, parentSpot):
        """Initialize a tree spot.

        Arguments:
            nodeRef -- reference to the associated tree node
            parentSpot -- the parent TreeSpot object
        """
        self.nodeRef = nodeRef
        self.parentSpot = parentSpot

    def index(self, modelRef):
        """Returns the index of this spot in the tree model.

        Arguments:
            modelRef -- a ref to the tree model
        """
        return modelRef.createIndex(self.row(), 0, self)

    def row(self):
        """Return the rank of this spot in its parent's child list.

        Should never be called from the imaginary root spot.
        """
        try:
            return self.parentSpot.nodeRef.childList.index(self.nodeRef)
        except ValueError:
            return 0  #  avoid error message from interim view updates

    def instanceNumber(self):
        """Return this spot's rank in the node's spot list.
        """
        spotList = sorted(list(self.nodeRef.spotRefs),
                          key=operator.methodcaller('sortKey'))
        return spotList.index(self)

    def spotId(self):
        """Return a spot ID string, in the form "nodeID:spotInstance".
        """
        return '{0}:{1:d}'.format(self.nodeRef.uId, self.instanceNumber())

    def isValid(self):
        """Return True if spot references and all parents are valid.
        """
        spot = self
        while spot.parentSpot:
            if not (spot in spot.nodeRef.spotRefs and
                    spot.nodeRef in spot.parentSpot.nodeRef.childList):
                return False
            spot = spot.parentSpot
        if not spot in spot.nodeRef.spotRefs:
            return False
        return True

    def spotDescendantGen(self):
        """Return a generator to step through all spots in this branch.

        Includes self.
        """
        yield self
        for childSpot in self.childSpots():
            for spot in childSpot.spotDescendantGen():
                yield spot

    def spotDescendantOnlyGen(self):
        """Return a generator to step through the spots in this branch.

        Does not include self.
        """
        for childSpot in self.childSpots():
            yield childSpot
            for spot in childSpot.spotDescendantGen():
                yield spot

    def expandedSpotDescendantGen(self, treeView):
        """Return a generator to step through expanded spots in this branch.

        Does not include root spot.
        Arguments:
            treeView -- a ref to the treeview
        """
        for childSpot in self.childSpots():
            if treeView.isSpotExpanded(childSpot):
                yield childSpot
                for spot in childSpot.expandedSpotDescendantGen(treeView):
                    yield spot

    def levelSpotDescendantGen(self, treeView, includeRoot=True, maxLevel=None,
                               openOnly=False, initLevel=0):
        """Return generator with (spot, level) tuples for this branch.

        Arguments:
            treeView -- a ref to the treeview, requiired to check if open
            includeRoot -- if True, the root spot is included
            maxLevel -- the max number of levels to return (no limit if none)
            openOnly -- if True, only include children open in the given view
            initLevel -- the level number to start with
        """
        if maxLevel == None:
            maxLevel = sys.maxsize
        if includeRoot:
            yield (self, initLevel)
            initLevel += 1
        if initLevel < maxLevel and (not openOnly or
                                     treeView.isSpotExpanded(self)):
            for childSpot in self.childSpots():
                for spot, level in childSpot.levelSpotDescendantGen(treeView,
                                                                    True,
                                                                    maxLevel,
                                                                    openOnly,
                                                                    initLevel):
                    yield (spot, level)

    def childSpots(self):
        """Return a list of immediate child spots.
        """
        return [childNode.matchedSpot(self) for childNode in
                self.nodeRef.childList]

    def prevSiblingSpot(self):
        """Return the nearest previous sibling spot or None.
        """
        if self.parentSpot:
            pos = self.row()
            if pos > 0:
                node = self.parentSpot.nodeRef.childList[pos - 1]
                return node.matchedSpot(self.parentSpot)
        return None

    def nextSiblingSpot(self):
        """Return the nearest next sibling spot or None.
        """
        if self.parentSpot:
            childList = self.parentSpot.nodeRef.childList
            pos = self.row() + 1
            if pos < len(childList):
                return childList[pos].matchedSpot(self.parentSpot)
        return None

    def prevTreeSpot(self, loop=False):
        """Return the previous node in the tree order.

        Return None at the start of the tree unless loop is true.
        Arguments:
            loop -- return the last node of the tree after the first if true
        """
        sibling = self.prevSiblingSpot()
        if sibling:
            return sibling.lastDescendantSpot()
        if self.parentSpot.parentSpot:
            return self.parentSpot
        elif loop:
            return self.rootSpot().lastDescendantSpot()
        return None

    def nextTreeSpot(self, loop=False):
        """Return the next node in the tree order.

        Return None at the end of the tree unless loop is true.
        Arguments:
            loop -- return the root node at the end of the tree if true
        """
        if self.nodeRef.childList:
            return self.nodeRef.childList[0].matchedSpot(self)
        ancestor = self
        while ancestor.parentSpot:
            sibling = ancestor.nextSiblingSpot()
            if sibling:
                return sibling
            ancestor = ancestor.parentSpot
        if loop:
            return ancestor.nodeRef.childList[0].matchedSpot(ancestor)
        return None

    def lastDescendantSpot(self):
        """Return the last spot of this spots's branch (last in tree order).
        """
        spot = self
        while spot.nodeRef.childList:
            spot = spot.nodeRef.childList[-1].matchedSpot(spot)
        return spot

    def spotChain(self):
        """Return a list of parent spots, including self.
        """
        chain = []
        spot = self
        while spot.parentSpot:
            chain.insert(0, spot)
            spot = spot.parentSpot
        return chain

    def parentSpotSet(self):
        """Return a set of ancestor spots, not including self.
        """
        result = set()
        spot = self.parentSpot
        while spot.parentSpot:
            result.add(spot)
            spot = spot.parentSpot
        return result

    def rootSpot(self):
        """Return the root spot that references the tree structure.
        """
        spot = self
        while spot.parentSpot:
            spot = spot.parentSpot
        return spot

    def sortKey(self):
        """Return a tuple of parent row positions for sorting in tree order.
        """
        positions = []
        spot = self
        while spot.parentSpot:
            positions.insert(0, spot.row())
            spot = spot.parentSpot
        return tuple(positions)
