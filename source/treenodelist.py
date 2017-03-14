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
