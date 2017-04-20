#!/usr/bin/env python3

#******************************************************************************
# treenode.py, provides a class to store tree node data
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import uuid
import treespot


class TreeNode:
    """Class to store tree node data and the tree's linked structure.

    Stores a data dict, lists of children and a format name string.
    Provides methods to get info on the structure and the data.
    """
    def __init__(self, formatRef, fileData=None):
        """Initialize a tree node.

        Arguments:
            formatRef -- a ref to this node's format info
            fileData -- a dict with uid, data, child refs & parent refs
        """
        self.formatRef = formatRef
        if not fileData:
            fileData = {}
        self.uId = fileData.get('uid', uuid.uuid1().hex)
        self.data = fileData.get('data', {})
        self.tmpChildRefs = fileData.get('children', [])
        self.childList = []
        self.spotRefs = set()

    def assignRefs(self, nodeDict):
        """Add actual refs to child nodes.

        Arguments:
            nodeDict -- all nodes stored by uid
        """
        self.childList = [nodeDict[uid] for uid in self.tmpChildRefs]
        self.tmpChildRefs = []

    def generateSpots(self, parentSpot):
        """Recursively generate spot references for this branch.

        Arguments:
            parentSpot -- the parent spot reference
        """
        spot = treespot.TreeSpot(self, parentSpot)
        self.spotRefs.add(spot)
        for child in self.childList:
            child.generateSpots(spot)

    def addSpotRef(self, parentNode):
        """Add a spot ref here to the given parent if not already there.

        If changed, propogate to descendant nodes.
        Arguments:
            parentNode -- the parent to ref in the new spot
        """
        changed = False
        origParentSpots = {spot.parentSpot for spot in self.spotRefs}
        if parentNode:
            for parentSpot in parentNode.spotRefs:
                if parentSpot not in origParentSpots:
                    self.spotRefs.add(treespot.TreeSpot(self, parentSpot))
                    changed = True
        elif None not in origParentSpots:
            self.spotRefs.add(treespot.TreeSpot(self, None))
            changed = True
        if changed:
            for child in self.childList:
                child.addSpotRef(self)

    def removeInvalidSpotRefs(self, includeChildren=True):
        """Verify existing spot refs and remove any that aren't valid.

        If changed and includeChilderen, propogate to descendant nodes.
        Arguments:
            includeChildren -- if True, propogate to descendant nodes
        """
        goodSpotRefs = {spot for spot in self.spotRefs if
                        (self in spot.parentSpot.nodeRef.childList and
                         spot.parentSpot in spot.parentSpot.nodeRef.spotRefs)}
        changed = len(self.spotRefs) != len(goodSpotRefs)
        self.spotRefs = goodSpotRefs
        if includeChildren and changed:
            for child in self.childList:
                child.removeInvalidSpotRefs(includeChildren)

    def setInitDefaultData(self, overwrite=False):
        """Add initial default data from fields into internal data.

        Arguments:
            overwrite -- if true, replace previous data entries
        """
        self.formatRef.setInitDefaultData(self.data, overwrite)

    def parents(self):
        """Return a set of parent nodes for this node.

        None is included for top level nodes.
        """
        return {spot.parentSpot.nodeRef if spot.parentSpot else None
                for spot in self.spotRefs}

    def numChildren(self):
        """Return number of children.
        """
        return len(self.childList)

    def descendantGen(self):
        """Return a generator to step through all nodes in this branch.

        Includes self and closed nodes.
        """
        yield self
        for child in self.childList:
            for node in child.descendantGen():
                yield node

    def matchedSpot(self, parentSpot):
        """Return the spot for this node that matches a parent spot.

        Return None if not found.
        Arguments:
            parentSpot -- the parent to match
        """
        for spot in self.spotRefs:
            if spot.parentSpot is parentSpot:
                return spot
        return None

    def fileData(self):
        """Return the file data dict for this node.
        """
        children = [node.uId for node in self.childList]
        fileData = {'format': self.formatRef.name, 'uid': self.uId,
                    'data': self.data, 'children': children}
        return fileData

    def title(self):
        """Return the title string for this node.
        """
        return self.formatRef.formatTitle(self)

    def setTitle(self, title):
        """Change this node's data based on a new title string.

        Return True if successfully changed.
        """
        if title == self.title():
            return False
        return self.formatRef.extractTitleData(title, self.data)

    def output(self, plainText=False, keepBlanks=False):
        """Return a list of formatted text output lines.

        Arguments:
            plainText -- if True, remove HTML markup from fields and formats
            keepBlanks -- if True, keep lines with empty fields
        """
        return self.formatRef.formatOutput(self, plainText, keepBlanks)

    def changeDataType(self, formatRef):
        """Change this node's data type to the given name.

        Set init default data and update the title if blank.
        Arguments:
            formatRef -- the new tree format type
        """
        origTitle = self.title()
        self.formatRef = formatRef
        formatRef.setInitDefaultData(self.data)
        if not formatRef.formatTitle(self):
            formatRef.extractTitleData(origTitle, self.data)

    def setData(self, field, editorText):
        """Set the data entry for the given field to editorText.

        If the data does not match the format, sets to the raw text and
        raises a ValueError.
        Arguments:
            field-- the field object to be set
            editorText -- new text data from an editor
        """
        try:
            self.data[field.name] = field.storedText(editorText)
        except ValueError:
            self.data[field.name] = editorText
            raise ValueError

    def replaceChildren(self, titleList, treeStructure):
        """Replace child nodes with titles from a text list.

        Nodes with matches in the titleList are kept, others are added or
        deleted as required.
        Arguments:
            titleList -- the list of new child titles
            treeStructure -- a ref to the tree structure
        """
        try:
            newFormat = treeStructure.treeFormats[self.formatRef.childType]
        except (KeyError, AttributeError):
            newFormat = (self.childList[0].formatRef if self.childList
                         else self.formatRef)
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
                    node = TreeNode(newFormat)
                    node.setTitle(title)
                    node.setInitDefaultData()
                    parent = self if self != treeStructure else None
                    node.addSpotRef(parent)
                    treeStructure.addNodeDictRef(node)
                firstMiss = False
            newChildList.append(node)
        for child in self.childList:
            for oldNode in child.descendantGen():
                if len(oldNode.parents()) <= 1:
                    treeStructure.removeNodeDictRef(oldNode)
                else:
                    oldNode.removeInvalidSpotRefs(False)
        self.childList = newChildList

    def replaceClonedBranches(self, origStruct):
        """Replace any duplicate IDs with clones from the given structure.

        Recursively search for duplicates.
        Arguments:
            origStruct -- the tree structure with the cloned nodes
        """
        for i in range(len(self.childList)):
            if self.childList[i].uId in origStruct.nodeDict:
                self.childList[i] = origStruct.nodeDict[self.childList[i].uId]
            else:
                self.childList[i].replaceClonedBranches(origStruct)

    def exportTitleText(self, level=0):
        """Return a list of tabbed title lines for this node and descendants.

        Arguments:
            level -- indicates the indent level needed
        """
        textList = ['\t' * level + self.title()]
        for child in self.childList:
            textList.extend(child.exportTitleText(level + 1, openOnly))
        return textList

