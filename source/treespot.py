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


class TreeSpot:
    """Class to store location info for tree node instances.

    Used to generate breadcrumb navigation and interface with tree views.
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
        return modelRef.createIndex(self.row(modelRef), 0, self)

    def row(self, modelRef):
        """Return the rank of this spot in its parent's child list.

        Arguments:
            modelRef -- a ref to the tree model
        """
        if self.parentSpot:
            return self.parentSpot.nodeRef.childList.index(self.nodeRef)
        return modelRef.treeStructure.childList.index(self.nodeRef)

    def prevSiblingSpot(self):
        """Return the nearest previous sibling spot or None.
        """
        if self.parentSpot:
            parentNode = self.parentSpot.nodeRef
            pos = parentNode.childList.index(self.nodeRef)
            if pos > 0:
                node = parentNode.childList[pos - 1]
                for spot in node.spotRefs:
                    if spot.parentSpot == self.parentSpot:
                        return spot
        return None

    def nextSiblingSpot(self):
        """Return the nearest next sibling spot or None.
        """
        if self.parentSpot:
            parentNode = self.parentSpot.nodeRef
            pos = parentNode.childList.index(self.nodeRef) + 1
            if pos < len(parentNode.childList):
                node = parentNode.childList[pos]
                for spot in node.spotRefs:
                    if spot.parentSpot == self.parentSpot:
                        return spot
        return None

    def spotChain(self):
        """Return a list of parent spots.
        """
        chain = []
        spot = self
        while spot:
            chain.insert(0, spot)
            spot = spot.parentSpot
        return chain

    def sortKey(self, modelRef):
        """Return a tuple of parent row positions for sorting in tree order.

        Arguments:
            modelRef -- a ref to the tree model
        """
        positions = []
        spot = self
        while spot:
            positions.insert(0, spot.row(modelRef))
            spot = spot.parentSpot
        return tuple(positions)
