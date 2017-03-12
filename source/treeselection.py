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

    def selectedNodes(self):
        """Return a TreeNodeList of the currently selected tree nodes.
        """
        return treenodelist.TreeNodeList([index.internalPointer() for index in
                                          self.selectedIndexes()])

    def currentNode(self):
        """Return the current tree node.
        """
        return self.currentIndex().internalPointer()

    def selectNode(self, node, signalUpdate=True, expandParents=False):
        """Clear the current selection and select the given node.

        Arguments:
            node -- the TreeNode to be selected
            signalUpdate -- if False, block normal right-view update signals
            expandParents -- open parent nodes to make selection visible
        """
        expandedNodes = []
        if expandParents:
            for expNode in self.tempExpandedNodes:
                expNode.collapseInView()
            self.tempExpandedNodes = []
            parent = node.parent
            while parent:
                if not parent.isExpanded():
                    parent.expandInView()
                    expandedNodes.append(parent)
                parent = parent.parent
        if not signalUpdate:
            self.blockSignals(True)
            self.addToHistory([node])
        self.clear()
        self.setCurrentIndex(node.index(), QItemSelectionModel.Select)
        self.blockSignals(False)
        self.tempExpandedNodes = expandedNodes

    def selectNodes(self, nodeList, signalUpdate=True, expandParents=False):
        """Clear the current selection and select the nodes in the given list.

        Arguments:
            nodeList -- a list of nodes to be selected.
            signalUpdate -- if False, block normal right-view update signals
            expandParents -- open parent nodes to make selection visible
        """
        expandedNodes = []
        if expandParents:
            for expNode in self.tempExpandedNodes:
                expNode.collapseInView()
            self.tempExpandedNodes = []
            for node in nodeList:
                parent = node.parent
                while parent:
                    if not parent.isExpanded():
                        parent.expandInView()
                        expandedNodes.append(parent)
                    parent = parent.parent
        if not signalUpdate:
            self.blockSignals(True)
            self.addToHistory(nodeList)
        self.clear()
        for node in nodeList:
            self.select(node.index(), QItemSelectionModel.Select)
        if nodeList:
            self.setCurrentIndex(nodeList[0].index(),
                                 QItemSelectionModel.Current)
        self.blockSignals(False)
        self.tempExpandedNodes = expandedNodes

    def sortSelection(self):
        """Sorts the selection by tree position.
        """
        self.selectNodes(sorted(self.selectedNodes(),
                                key=operator.methodcaller('treePosSortKey')),
                         False)
