#!/usr/bin/env python3

#******************************************************************************
# treespot.py, provides a class to store locations of tree node instances
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

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
        return self.parentSpot.nodeRef.childList.index(self.nodeRef)

    def instanceNumber(self):
        """Return this spot's rank in the node's spot list.
        """
        spotList = sorted(list(self.nodeRef.spotRefs),
                          key=operator.methodcaller('sortKey'))
        return spotList.index(self)

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

    def prevSiblingSpot(self):
        """Return the nearest previous sibling spot or None.
        """
        if self.parentSpot:
            pos = self.row()
            if pos > 0:
                node = self.parentSpot.nodeRef.childList[pos - 1]
                for spot in node.spotRefs:
                    if spot.parentSpot == self.parentSpot:
                        return spot
        return None

    def nextSiblingSpot(self):
        """Return the nearest next sibling spot or None.
        """
        if self.parentSpot:
            childList = self.parentSpot.nodeRef.childList
            pos = self.row() + 1
            if pos < len(childList):
                node = childList[pos]
                for spot in node.spotRefs:
                    if spot.parentSpot == self.parentSpot:
                        return spot
        return None

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

    def sortKey(self):
        """Return a tuple of parent row positions for sorting in tree order.
        """
        positions = []
        spot = self
        while spot.parentSpot:
            positions.insert(0, spot.row())
            spot = spot.parentSpot
        return tuple(positions)
