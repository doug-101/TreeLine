#!/usr/bin/env python3

#******************************************************************************
# treenodelist.py, provides a class to do operations on groups of nodes
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
from PyQt5.QtCore import QMimeData
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import (QApplication, QMessageBox)
import treestructure
import undo


class TreeNodeList(list):
    """Class to do operations on groups of nodes.

    Stores a list of nodes.
    """
    def __init__(self, nodeList=None, removeDuplicates=True):
        """Initialize a tree node group.

        Arguments:
            nodeList -- the initial list of nodes
            removeDuplicates -- if True, remove duplicated nodes from the list
        """
        super().__init__()
        if nodeList:
            self[:] = nodeList
            if removeDuplicates:
                tmpDict = collections.OrderedDict()
                for node in self:
                    tmpDict[node.uId] = node
                self[:] = list(tmpDict.values())

    def copyNodes(self):
        """Copy these node branches to the clipboard.
        """
        if not self:
            return
        clip = QApplication.clipboard()
        if clip.supportsSelection():
            titleList = []
            for node in self:
                titleList.extend(node.exportTitleText())
            clip.setText('\n'.join(titleList), QClipboard.Selection)
        data = treestructure.TreeStructure(topNodes=self,
                                           addSpots=False).fileData()
        dataStr = json.dumps(data, indent=0, sort_keys=True)
        mime = QMimeData()
        mime.setData('application/json', bytes(dataStr, encoding='utf-8'))
        clip.setMimeData(mime)

    def pasteNodes(self, treeStructure):
        """Paste nodes from clipboard mime data under these parent nodes.

        Return True on success.
        Arguments:
            treeSstructure -- the existing parent structure
        """
        mimeData = QApplication.clipboard().mimeData()
        parents = self if self else [treeStructure]
        undoObj = undo.ChildListFormatUndo(treeStructure.undoList, parents,
                                           treeStructure.treeFormats)
        for parent in parents:
            newStruct = treestructure.structFromMimeData(mimeData)
            if not newStruct:
                treeStructure.undoList.removeLastUndo(undoObj)
                return False
            newStruct.replaceDuplicateIds(treeStructure.nodeDict)
            treeStructure.addNodesFromStruct(newStruct, parent)
        return True

    def pasteClones(self, treeStructure):
        """Paste cloned nodes from clipboard mime data under these nodes.

        Return True on success.
        Arguments:
            treeSstructure -- the existing parent structure
        """
        mimeData = QApplication.clipboard().mimeData()
        newStruct = treestructure.structFromMimeData(mimeData)
        if newStruct:
            try:
                existNodes = [treeStructure.nodeDict[node.uId] for node in
                              newStruct.childList]
            except KeyError:
                return False  # nodes copied from other file
            parents = self if self else [treeStructure]
            for parent in parents:
                if not parent.ancestors().isdisjoint(set(existNodes)):
                    return False  # circular ref
                for node in existNodes:
                    if parent in node.parents():
                        return False  # identical siblings
            undoObj = undo.ChildListFormatUndo(treeStructure.undoList, parents,
                                               treeStructure.treeFormats)
            for parent in parents:
                for node in existNodes:
                    parent.childList.append(node)
                    node.addSpotRef(parent)
            return True
        return False
