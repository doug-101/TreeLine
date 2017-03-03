#!/usr/bin/env python3

#******************************************************************************
# treeformats.py, provides a class to store node format types and info
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
import nodeformat


defaultTypeName = _('DEFAULT')

class TreeFormats(dict):
    """Class to store node format types and info.

    Stores node formats by format name in a dictionary.
    Provides methods to change and update format data.
    """
    def __init__(self, formatList=None, setDefault=False):
        """Initialize the format storage.

        Arguments:
            formatList -- the list of formats' file info
            setDefault - if true, initializes with a default format
        """
        super().__init__()
        if formatList:
            for formatData in formatList:
                name = formatData['formatname']
                self[name] = nodeformat.NodeFormat(name, formatData)
        if setDefault:
            self[defaultTypeName] = nodeformat.NodeFormat(defaultTypeName,
                                                          addDefaultField=True)

    def storeFormats(self):
        """Return a list of formats stored in JSON data.
        """
        return sorted([nodeFormat.storeFormat() for nodeFormat in
                       self.values()],
                      key=operator.itemgetter('formatname'))

    def typeNames(self):
        """Return a sorted list of type names.
        """
        return sorted(list(self.keys()))

    def updateLineParsing(self):
        """Update the fields parsed in the output lines for each format type.
        """
        for typeFormat in self.values():
            typeFormat.updateLineParsing()

    def addTypeIfMissing(self, typeFormat):
        """Add format to available types if not a duplicate.

        Arguments:
            typeFormat -- the node format to add
        """
        self.setdefault(typeFormat.name, typeFormat)
