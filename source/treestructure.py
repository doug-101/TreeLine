#!/usr/bin/env python3

#******************************************************************************
# treestructure.py, provides a class to store the tree's data
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import json
import operator
import treenode
import treeformats
try:
    from __main__ import __version__
except ImportError:
    __version__ = ''

_defaultRootTitle = _('Main')


class TreeStructure:
    """Class to store all tree data.
    """
    def __init__(self, fileObj=None, addDefaults=False):
        """Retrive a TreeLine file to create a tree structure.

        If no file object is given, create an empty or a default new structure.
        Arguments:
            fileObj -- a file-like object
            addDefaults - if true, adds default new structure
        """
        self.nodeDict = {}
        self.childList = []  # top-level nodes
        self.data = {}  # empty placeholder for duck-typing as the "top node"
        self.spotRefs = set()  # empty placeholder for duck-typing
        self.undoList = None
        self.redoList = None
        if fileObj:
            fileData = json.load(fileObj)
            self.treeFormats = treeformats.TreeFormats(fileData['formats'])
            for nodeInfo in fileData['nodes']:
                formatRef = self.treeFormats[nodeInfo['format']]
                node = treenode.TreeNode(formatRef, nodeInfo)
                self.nodeDict[node.uId] = node
            for node in self.nodeDict.values():
                node.assignRefs(self.nodeDict)
            for uid in fileData['properties']['topnodes']:
                node = self.nodeDict[uid]
                self.childList.append(node)
                node.generateSpots(None)
        elif addDefaults:
            self.treeFormats = treeformats.TreeFormats(setDefault=True)
            node = treenode.TreeNode(self.treeFormats[treeformats.
                                                      defaultTypeName])
            node.setTitle(_defaultRootTitle)
            self.nodeDict[node.uId] = node
            self.childList.append(node)
            node.generateSpots(None)
        else:
            self.treeFormats = treeformats.TreeFormats()

    def storeFile(self, fileObj):
        """Save a TreeLine file.

        Arguments:
            fileObj -- a file-like object
        """
        formats = self.treeFormats.storeFormats()
        nodeList = sorted([node.fileData() for node in self.nodeDict.values()],
                          key=operator.itemgetter('uid'))
        topNodeIds = [node.uId for node in self.childList]
        properties = {'tlversion': __version__, 'topnodes': topNodeIds}
        fileData = {'formats': formats, 'nodes': nodeList,
                    'properties': properties}
        json.dump(fileData, fileObj, indent=3, sort_keys=True)

    def addNodeDictRef(self, node):
        """Add the given node to the node dictionary.

        Arguments:
            node -- the node to add
        """
        self.nodeDict[node.uId] = node

    def removeNodeDictRef(self, node):
        """Remove the given node from the node dictionary.

        Arguments:
            node -- the node to remove
        """
        try:
            del self.nodeDict[node.uId]
        except KeyError:
            pass

    def descendantGen(self):
        """Return a generator to step through all nodes in this branch.

        Includes structure "node" and closed nodes.
        """
        yield self
        for child in self.childList:
            for node in child.descendantGen():
                yield node

    def updateChildSpots(self):
        """Create new spot references for descendants of this structure.
        """
        for child in self.childList:
            child.updateChildSpots()

    def replaceChildren(self, titleList, treeStructure):
        """Replace child nodes with titles from a text list.

        Nodes with matches in the titleList are kept, others are added or
        deleted as required.
        Arguments:
            titleList -- the list of new child titles
            treeStructure -- a ref to the tree structure
        """
        newFormat = self.childList[0].formatRef
        matchList = []
        remainTitles = [child.title() for child in self.childList]
        for title in titleList:
            try:
                match = self.childList.pop(remainTitles.index(title))
                matchList.append((title, match))
                remainTitles = [child.title() for child in self.childList]
            except ValueError:
                matchList.append((title, None))
        newChildList = []
        firstMiss = True
        for title, node in matchList:
            if not node:
                if (firstMiss and remainTitles and
                    remainTitles[0].startswith(title)):
                    # accept partial match on first miss for split tiles
                    node = self.childList.pop(0)
                    node.setTitle(title)
                else:
                    node = treenode.TreeNode(newFormat)
                    node.setTitle(title)
                    node.setInitDefaultData()
                    treeStructure.addNodeDictRef(node)
                    node.generateSpots(None)
                firstMiss = False
            newChildList.append(node)
        for child in self.childList:
            for oldNode in child.descendantGen():
                if len(oldNode.parents()) <= 1:
                    treeStructure.removeNodeDictRef(oldNode)
        self.childList = newChildList
