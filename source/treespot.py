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
