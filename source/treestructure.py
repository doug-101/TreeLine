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
        self.topNodes = []
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
                self.topNodes.append(node)
                node.generateSpots(None)
        elif addDefaults:
            self.treeFormats = treeformats.TreeFormats(setDefault=True)
            node = treenode.TreeNode(self.treeFormats[treeformats.
                                                      defaultTypeName])
            node.setTitle(_defaultRootTitle)
            self.nodeDict[node.uId] = node
            self.topNodes.append(node)
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
        topNodeIds = [node.uId for node in self.topNodes]
        properties = {'tlversion': __version__, 'topnodes': topNodeIds}
        fileData = {'formats': formats, 'nodes': nodeList,
                    'properties': properties}
        json.dump(fileData, fileObj, indent=3, sort_keys=True)
