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
import operator
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
        for parentSpot in parentNode.spotRefs:
            if parentSpot not in origParentSpots:
                self.spotRefs.add(treespot.TreeSpot(self, parentSpot))
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

    def spotByNumber(self, num):
        """Return the spot at the given rank in the spot sequence.

        Arguments:
            num -- the rank number to return
        """
        spotList = sorted(list(self.spotRefs),
                          key=operator.methodcaller('sortKey'))
        return spotList[num]

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

    def setInitDefaultData(self, overwrite=False):
        """Add initial default data from fields into internal data.

        Arguments:
            overwrite -- if true, replace previous data entries
        """
        self.formatRef.setInitDefaultData(self.data, overwrite)

    def parents(self):
        """Return a set of parent nodes for this node.

        Returns an empty set if called from the tree structure..
        """
        try:
            return {spot.parentSpot.nodeRef for spot in self.spotRefs}
        except AttributeError:
            return set()

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

    def ancestors(self):
        """Return a set of all ancestor nodes (including self).
        """
        spots = set()
        for spot in self.spotRefs:
            spots.update(spot.spotChain())
        return {spot.nodeRef for spot in spots}

    def treeStructureRef(self):
        """Return the tree structure based on the root spot ref.
        """
        return next(iter(self.spotRefs)).rootSpot().nodeRef

    def fileData(self):
        """Return the file data dict for this node.
        """
        children = [node.uId for node in self.childList]
        fileData = {'format': self.formatRef.name, 'uid': self.uId,
                    'data': self.data, 'children': children}
        return fileData

    def title(self, spotRef=None):
        """Return the title string for this node.

        If spotRef not given, ancestor fields assume first spot
        Arguments:
            spotRef -- optional, used for ancestor field refs
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
        except ValueError as err:
            if len(err.args) >= 2:
                self.data[field.name] = err.args[1]
            else:
                self.data[field.name] = editorText
            raise ValueError

    def wordSearch(self, wordList, titleOnly=False, spotRef=None):
        """Return True if all words in wordlist are found in this node's data.

        Arguments:
            wordList -- a list of words or phrases to find
            titleOnly -- search only in the title text if True
            spotRef -- an optional spot reference for ancestor field refs
        """
        dataStr = self.title(spotRef).lower()
        if not titleOnly:
            # join with null char so phrase matches don't cross borders
            dataStr = '{0}\0{1}'.format(dataStr,
                                        '\0'.join(self.data.values()).lower())
        for word in wordList:
            if word not in dataStr:
                return False
        return True

    def regExpSearch(self, regExpList, titleOnly=False, spotRef=None):
        """Return True if the regular expression is found in this node's data.

        Arguments:
            regExpList -- a list of regular expression objects to find
            titleOnly -- search only in the title text if True
            spotRef -- an optional spot reference for ancestor field refs
        """
        dataStr = self.title(spotRef)
        if not titleOnly:
            # join with null char so phrase matches don't cross borders
            dataStr = '{0}\0{1}'.format(dataStr, '\0'.join(self.data.values()))
        for regExpObj in regExpList:
            if not regExpObj.search(dataStr):
                return False
        return True

    def addNewChild(self, treeStructure, posRefNode=None, insertBefore=True,
                    newTitle=_('New')):
        """Add a new child node with this node as the parent.

        Insert the new node near the posRefNode or at the end if no ref node.
        Return the new node.
        Arguments:
            treeStructure -- a ref to the tree structure
            posRefNode -- a child reference for the new node's position
            insertBefore -- insert before the ref node if True, after if False
        """
        try:
            newFormat = treeStructure.treeFormats[self.formatRef.childType]
        except (KeyError, AttributeError):
            if posRefNode:
                newFormat = posRefNode.formatRef
            elif self.childList:
                newFormat = self.childList[0].formatRef
            else:
                newFormat = self.formatRef
        newNode = TreeNode(newFormat)
        pos = len(self.childList)
        if posRefNode:
            pos = self.childList.index(posRefNode)
            if not insertBefore:
                pos += 1
        self.childList.insert(pos, newNode)
        newNode.setInitDefaultData()
        if newTitle and not newNode.title():
            newNode.setTitle(newTitle)
        newNode.addSpotRef(self)
        treeStructure.addNodeDictRef(newNode)
        return newNode

    def changeParent(self, oldParent, newParent, newPos=-1):
        """Move this node from oldParent to newParent.

        Used for indent and unindent commands.
        Arguments:
            oldParent -- the original parent node
            newParent -- the new parent node
            newPos -- the position in the new childList, -1 for append
        """
        oldParent.childList.remove(self)
        if newPos >= 0:
            newParent.childList.insert(newPos, self)
        else:
            newParent.childList.append(self)
        self.removeInvalidSpotRefs()
        self.addSpotRef(newParent)

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
                    node.addSpotRef(self)
                    treeStructure.addNodeDictRef(node)
                firstMiss = False
            newChildList.append(node)
        for child in self.childList:
            for oldNode in child.descendantGen():
                if len(oldNode.spotRefs) <= 1:
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

    def loadChildLevels(self, textLevelList, structure, initLevel=0):
        """Recursively add children from a list of text titles and levels.

        Return True on success, False if data levels are not valid.
        Arguments:
            textLevelList -- list of tuples with title text and level
            structure -- a ref to the tree structure
            initLevel -- the level of this node in the structure
        """
        while textLevelList:
            text, level = textLevelList[0]
            if level == initLevel + 1:
                del textLevelList[0]
                child = TreeNode(self.formatRef)
                child.setTitle(text)
                self.childList.append(child)
                structure.addNodeDictRef(child)
                if not child.loadChildLevels(textLevelList, structure, level):
                    return False
            else:
                return -1 < level <= initLevel
        return True

    def exportTitleText(self, level=0):
        """Return a list of tabbed title lines for this node and descendants.

        Arguments:
            level -- indicates the indent level needed
        """
        textList = ['\t' * level + self.title()]
        for child in self.childList:
            textList.extend(child.exportTitleText(level + 1))
        return textList
