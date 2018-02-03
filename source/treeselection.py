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

import collections
import json
from PyQt5.QtCore import QItemSelectionModel, QMimeData
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import QApplication
import treestructure
import treespotlist
import globalref


_maxHistoryLength = 10

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
        self.tempExpandedSpots = []
        self.prevSpots = []
        self.nextSpots = []
        self.restoreFlag = False
        self.selectionChanged.connect(self.updateSelectLists)

    def selectedCount(self):
        """Return the number of selected spots.
        """
        return len(self.selectedIndexes())

    def selectedSpots(self):
        """Return a SpotList of selected spots, sorted in tree order.
        """
        return treespotlist.TreeSpotList([index.internalPointer() for index in
                                          self.selectedIndexes()])

    def selectedBranchSpots(self):
        """Return a list of spots at the top of selected branches.

        Remvoves any duplicate spots that are already covered by the branches.
        """
        spots = self.selectedSpots()
        spotSet = set(spots)
        return [spot for spot in spots if
                spot.parentSpotSet().isdisjoint(spotSet)]

    def selectedNodes(self):
        """Return a list of the currently selected tree nodes.

        Removes any duplicate (cloned) nodes.
        """
        tmpDict = collections.OrderedDict()
        for spot in self.selectedSpots():
            node = spot.nodeRef
            tmpDict[node.uId] = node
        return list(tmpDict.values())

    def selectedBranches(self):
        """Return a list of nodes at the top of selected branches.

        Remvoves any duplicates that are already covered by the branches.
        """
        tmpDict = collections.OrderedDict()
        for spot in self.selectedBranchSpots():
            node = spot.nodeRef
            tmpDict[node.uId] = node
        return list(tmpDict.values())

    def currentSpot(self):
        """Return the current tree spot.

        Can raise AttributeError if no spot is current.
        """
        return self.currentIndex().internalPointer()

    def currentNode(self):
        """Return the current tree node.

        Can raise AttributeError if no node is current.
        """
        return self.currentSpot().nodeRef

    def selectSpots(self, spotList, signalUpdate=True, expandParents=False):
        """Clear the current selection and select the given spots.

        Arguments:
            spotList -- the spots to select
            signalUpdate -- if False, block normal select update signals
            expandParents -- open parent spots to make selection visible
        """
        if expandParents:
            treeView = (globalref.mainControl.activeControl.activeWindow.
                        treeView)
            for spot in self.tempExpandedSpots:
                treeView.collapseSpot(spot)
            self.tempExpandedSpots = []
            for spot in spotList:
                parent = spot.parentSpot
                while parent.parentSpot:
                    if not treeView.isSpotExpanded(parent):
                        treeView.expandSpot(parent)
                        self.tempExpandedSpots.append(parent)
                    parent = parent.parentSpot
        if not signalUpdate:
            self.blockSignals(True)
            self.addToHistory(spotList)
        self.clear()
        if spotList:
            for spot in spotList:
                self.select(spot.index(self.modelRef),
                            QItemSelectionModel.Select)
            self.setCurrentIndex(spotList[0].index(self.modelRef),
                                 QItemSelectionModel.Current)
        self.blockSignals(False)

    def selectNodeById(self, nodeId):
        """Select the first spot from the given node ID.

        Return True on success.
        Arguments:
            nodeId -- the ID of the node to select
        """
        try:
            node = self.modelRef.treeStructure.nodeDict[nodeId]
            self.selectSpots([node.spotByNumber(0)], True, True)
        except KeyError:
            return False
        return True

    def setCurrentSpot(self, spot):
        """Set the current spot.

        Arguments:
            spot -- the spot to make current
        """
        self.blockSignals(True)
        self.setCurrentIndex(spot.index(self.modelRef),
                             QItemSelectionModel.Current)
        self.blockSignals(False)

    def copySelectedNodes(self):
        """Copy these node branches to the clipboard.
        """
        nodes = self.selectedBranches()
        if not nodes:
            return
        clip = QApplication.clipboard()
        if clip.supportsSelection():
            titleList = []
            for node in nodes:
                titleList.extend(node.exportTitleText())
            clip.setText('\n'.join(titleList), QClipboard.Selection)
        struct = treestructure.TreeStructure(topNodes=nodes, addSpots=False)
        generics = {formatRef.genericType for formatRef in
                    struct.treeFormats.values() if formatRef.genericType}
        for generic in generics:
            genericRef = self.modelRef.treeStructure.treeFormats[generic]
            struct.treeFormats.addTypeIfMissing(genericRef)
            for formatRef in genericRef.derivedTypes:
                struct.treeFormats.addTypeIfMissing(formatRef)
        data = struct.fileData()
        dataStr = json.dumps(data, indent=0, sort_keys=True)
        mime = QMimeData()
        mime.setData('application/json', bytes(dataStr, encoding='utf-8'))
        clip.setMimeData(mime)

    def restorePrevSelect(self):
        """Go back to the most recent saved selection.
        """
        self.validateHistory()
        if len(self.prevSpots) > 1:
            del self.prevSpots[-1]
            oldSelect = self.selectedSpots()
            if oldSelect and (not self.nextSpots or
                              oldSelect != self.nextSpots[-1]):
                self.nextSpots.append(oldSelect)
            self.restoreFlag = True
            self.selectSpots(self.prevSpots[-1], expandParents=True)
            self.restoreFlag = False

    def restoreNextSelect(self):
        """Go forward to the most recent saved selection.
        """
        self.validateHistory()
        if self.nextSpots:
            select = self.nextSpots.pop(-1)
            if select and (not self.prevSpots or
                           select != self.prevSpots[-1]):
                self.prevSpots.append(select)
            self.restoreFlag = True
            self.selectSpots(select, expandParents=True)
            self.restoreFlag = False

    def addToHistory(self, spots):
        """Add given spots to previous select list.

        Arguments:
            spots -- a list of spots to be added
        """
        if spots and not self.restoreFlag and (not self.prevSpots or
                                               spots != self.prevSpots[-1]):
            self.prevSpots.append(spots)
            if len(self.prevSpots) > _maxHistoryLength:
                del self.prevSpots[:2]
            self.nextSpots = []

    def validateHistory(self):
        """Clear invalid items from history lists.
        """
        for histList in (self.prevSpots, self.nextSpots):
            for spots in histList:
                spots[:] = [spot for spot in spots if spot.isValid()]
            histList[:] = [spots for spots in histList if spots]

    def updateSelectLists(self):
        """Update history after a selection change.
        """
        self.addToHistory(self.selectedSpots())

    def selectTitleMatch(self, searchText, forward=True, includeCurrent=False):
        """Select a node with a title matching the search text.

        Returns True if found, otherwise False.
        Arguments:
            searchText -- the text to look for
            forward -- next if True, previous if False
            includeCurrent -- look in current node if True
        """
        searchText = searchText.lower()
        currentSpot = self.currentSpot()
        spot = currentSpot
        while True:
            if not includeCurrent:
                if forward:
                    spot = spot.nextTreeSpot(True)
                else:
                    spot = spot.prevTreeSpot(True)
                if spot is currentSpot:
                    return False
            includeCurrent = False
            if searchText in spot.nodeRef.title().lower():
                self.selectSpots([spot], True, True)
                return True
