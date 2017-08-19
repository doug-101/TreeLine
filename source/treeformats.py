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
import copy
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
        # new names for types renamed in the config dialog (orig names as keys)
        self.typeRenameDict = {}
        # nested dict for fields renamed, keys are type name then orig field
        self.fieldRenameDict = {}
        self.conditionalTypes = set()
        self.fileInfoFormat = nodeformat.FileInfoFormat(self)
        if formatList:
            for formatData in formatList:
                name = formatData['formatname']
                self[name] = nodeformat.NodeFormat(name, self, formatData)
            self.updateDerivedRefs()
        if nodeformat.FileInfoFormat.typeName in self:
            self.fileInfoFormat.duplicateFileInfo(self[nodeformat.
                                                       FileInfoFormat.
                                                       typeName])
            del self[nodeformat.FileInfoFormat.typeName]
        if setDefault:
            self[defaultTypeName] = nodeformat.NodeFormat(defaultTypeName,
                                                          self,
                                                          addDefaultField=True)

    def storeFormats(self):
        """Return a list of formats stored in JSON data.
        """
        formats = list(self.values())
        if self.fileInfoFormat.fieldFormatModified:
            formats.append(self.fileInfoFormat)
        return sorted([nodeFormat.storeFormat() for nodeFormat in formats],
                      key=operator.itemgetter('formatname'))

    def copySettings(self, sourceFormats):
        """Copy all settings from other type formats to these formats.

        Copy any new formats and delete any missing formats.
        Arguments:
            sourceFormats -- the type formats to copy
        """
        if sourceFormats.typeRenameDict:
            for oldName, newName in sourceFormats.typeRenameDict.items():
                self[oldName].name = newName
            formats = list(self.values())
            self.clear()
            for nodeFormat in formats:
                self[nodeFormat.name] = nodeFormat
            sourceFormats.typeRenameDict = {}
        for name in list(self.keys()):
            if name in sourceFormats:
                self[name].copySettings(sourceFormats[name])
            else:
                del self[name]
        for name in sourceFormats.keys():
            if name not in self:
                self[name] = copy.deepcopy(sourceFormats[name])
        if (sourceFormats.fileInfoFormat.fieldFormatModified or
            self.fileInfoFormat.fieldFormatModified):
            self.fileInfoFormat.duplicateFileInfo(sourceFormats.fileInfoFormat)

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

    def updateDerivedRefs(self):
        """Update derived type lists (in generics) & the conditional type set.
        """
        self.conditionalTypes = set()
        for typeFormat in self.values():
            typeFormat.derivedTypes = []
            # if typeFormat.conditional:
                # self.conditionalTypes.add(typeFormat)
                # if typeFormat.genericType:
                    # self.conditionalTypes.add(self[typeFormat.genericType])
        for typeFormat in self.values():
            if typeFormat.genericType:
                genericType = self[typeFormat.genericType]
                genericType.derivedTypes.append(typeFormat)
                if genericType in self.conditionalTypes:
                    self.conditionalTypes.add(typeFormat)
        for typeFormat in self.values():
            if not typeFormat.genericType and not typeFormat.derivedTypes:
                # typeFormat.conditional = conditional.Conditional()
                self.conditionalTypes.discard(typeFormat)
