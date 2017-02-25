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


class TreeStructure:
    """Class to store all tree data.
    """
    def __init__(self):
        """Initialize a TreeStructure.
        """
        self.nodeDict = {}
        self.topNodes = []
        self.treeFormats = None

    def loadFile(self, fileObj):
        """Retrive a TreeLine file.

        Arguments:
            fileObj -- a file-like object
        """
        fileData = json.load(fileObj)
        for nodeInfo in fileData['nodes']:
            node = treenode.TreeNode(nodeInfo['format'], nodeInfo)
            self.nodeDict[node.uId] = node
        for node in self.nodeDict.values():
            node.assignRefs(self.nodeDict)
            # print(node.data['Name'])
        for uid in fileData['properties']['topnodes']:
            node = self.nodeDict[uid]
            self.topNodes.append(node)
            node.generateSpots(None)

    def storeFile(self, fileObj):
        """Save a TreeLine file.

        Arguments:
            fileObj -- a file-like object
        """
        formats = []
        nodeList = sorted([node.fileData() for node in self.nodeDict.values()],
                          key=operator.itemgetter('uid'))
        topNodeIds = [node.uId for node in self.topNodes]
        properties = {'tlversion': '2.9.0', 'topnodes': topNodeIds}
        fileData = {'formats': formats, 'nodes': nodeList,
                    'properties': properties}
        json.dump(fileData, fileObj, indent=3, sort_keys=True)
