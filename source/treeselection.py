#!/usr/bin/env python3

#******************************************************************************
# treeselection.py, provides a class for the tree view's selection model
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
from PyQt5.QtCore import QItemSelectionModel
import treenodelist


class TreeSelection(QItemSelectionModel):
    """Class override for the tree view's selection model.

    Provides methods for easier access to selected nodes.
    """
    def __init__(self, model, parent=None):
        """Initialize the selection model.

        Arguments:
            model -- the model for view data
            parent -- the parent tree view
        """
        super().__init__(model, parent)
        self.modelRef = model

    def selectedSpots(self):
        """Return a list of selected spots, sorted in tree order.
        """
        spots = [index.internalPointer() for index in self.selectedIndexes()]
        return sorted(spots,
                      key=operator.methodcaller('sortKey', self.modelRef))

    def selectedNodes(self):
        """Return a TreeNodeList of the currently selected tree nodes.

        Removes any duplicate (cloned) nodes.
        """
        return treenodelist.TreeNodeList([spot.nodeRef for spot in
                                          self.selectedSpots()])

    def currentSpot(self):
        """Return the current tree spot.
        """
        return self.currentIndex().internalPointer()

    def currentNode(self):
        """Return the current tree node.
        """
        return self.currentSpot().nodeRef

    def selectSpots(self, spotList, signalUpdate=True):
        """Clear the current selection and select the given spots.

        Arguments:
            spotList -- the spots to select
            signalUpdate -- if False, block normal select update signals
        """
        if not signalUpdate:
            self.blockSignals(True)
        self.clear()
        if spotList:
            for spot in spotList:
                self.select(spot.index(self.modelRef),
                            QItemSelectionModel.Select)
            self.setCurrentIndex(spotList[0].index(self.modelRef),
                                 QItemSelectionModel.Current)
        self.blockSignals(False)
