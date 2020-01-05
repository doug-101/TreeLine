#!/usr/bin/env python3

#******************************************************************************
# treenode.py, provides a class to store tree node data
#
# TreeLine, an information storage program
# Copyright (C) 2020, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re
import uuid
import operator
import itertools
import treespot
import nodeformat

_replaceBackrefRe = (re.compile(r'\\(\d+)'), re.compile(r'\\g<(\d+)>'))
_origBackrefMatch = None


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
        """Add actual refs to child nodes from data in self.tmpChildRefs.

        Any bad node refs (corrupt file data) are left in self.tmpChildRefs.
        Arguments:
            nodeDict -- all nodes stored by uid
        """
        try:
            self.childList = [nodeDict[uid] for uid in self.tmpChildRefs]
            self.tmpChildRefs = []
        except KeyError:   # due to corrupt file data
            badChildRefs = []
            for uid in self.tmpChildRefs:
                if uid in nodeDict:
                    self.childList.append(nodeDict[uid])
                else:
                    badChildRefs.append(uid)
            self.tmpChildRefs = badChildRefs

    def generateSpots(self, parentSpot):
        """Recursively generate spot references for this branch.

        Arguments:
            parentSpot -- the parent spot reference
        """
        spot = treespot.TreeSpot(self, parentSpot)
        self.spotRefs.add(spot)
        for child in self.childList:
            child.generateSpots(spot)

    def addSpotRef(self, parentNode, includeChildren=True):
        """Add a spot ref here to the given parent if not already there.

        If changed, propogate to descendant nodes.
        Arguments:
            parentNode -- the parent to ref in the new spot
            includeChildren -- if True, propogate to descendant nodes
        """
        changed = False
        origParentSpots = {spot.parentSpot for spot in self.spotRefs}
        for parentSpot in parentNode.spotRefs:
            if parentSpot not in origParentSpots:
                self.spotRefs.add(treespot.TreeSpot(self, parentSpot))
                changed = True
        if changed and includeChildren:
            for child in self.childList:
                child.addSpotRef(self)

    def removeInvalidSpotRefs(self, includeChildren=True, forceDesend=False):
        """Verify existing spot refs and remove any that aren't valid.

        If changed and includeChilderen, propogate to descendant nodes.
        Arguments:
            includeChildren -- if True, propogate to descendants if changes
            forceDesend -- if True, force propogate to descendant nodes
        """
        goodSpotRefs = {spot for spot in self.spotRefs if
                        (self in spot.parentSpot.nodeRef.childList and
                         spot.parentSpot in spot.parentSpot.nodeRef.spotRefs)}
        changed = len(self.spotRefs) != len(goodSpotRefs)
        self.spotRefs = goodSpotRefs
        if includeChildren and (changed or forceDesend):
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

        Returns an empty set if called from the tree structure.
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

        If spotRef not given, ancestor fields assume first spot.
        Arguments:
            spotRef -- optional, used for ancestor field refs
        """
        return self.formatRef.formatTitle(self, spotRef)

    def setTitle(self, title):
        """Change this node's data based on a new title string.

        Return True if successfully changed.
        """
        if title == self.title():
            return False
        return self.formatRef.extractTitleData(title, self.data)

    def output(self, plainText=False, keepBlanks=False, spotRef=None):
        """Return a list of formatted text output lines.

        If spotRef not given, ancestor fields assume first spot.
        Arguments:
            plainText -- if True, remove HTML markup from fields and formats
            keepBlanks -- if True, keep lines with empty fields
            spotRef -- optional, used for ancestor field refs
        """
        return self.formatRef.formatOutput(self, plainText, keepBlanks,
                                           spotRef)

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

    def setConditionalType(self, treeStructure):
        """Set self to type based on auto conditional settings.

        Return True if type is changed.
        Arguments:
            treeStructure -- a ref to the tree structure
        """
        if self.formatRef not in treeStructure.treeFormats.conditionalTypes:
            return False
        if self.formatRef.genericType:
            genericFormat = treeStructure.treeFormats[self.formatRef.
                                                      genericType]
        else:
            genericFormat = self.formatRef
        formatList = [genericFormat] + genericFormat.derivedTypes
        formatList.remove(self.formatRef)
        formatList.insert(0, self.formatRef)   # reorder to give priority
        neutralResult = None
        newType = None
        for typeFormat in formatList:
            if typeFormat.conditional:
                if typeFormat.conditional.evaluate(self):
                    newType = typeFormat
                    break
            elif not neutralResult:
                neutralResult = typeFormat
        if not newType and neutralResult:
            newType = neutralResult
        if newType and newType is not self.formatRef:
            self.changeDataType(newType)
            return True
        return False

    def setDescendantConditionalTypes(self, treeStructure):
        """Set auto conditional types for self and all descendants.

        Return number of changes made.
        Arguments:
            treeStructure -- a ref to the tree structure
        """
        if not treeStructure.treeFormats.conditionalTypes:
            return 0
        changes = 0
        for node in self.descendantGen():
            if node.setConditionalType(treeStructure):
                changes += 1
        return changes

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

    def searchReplace(self, searchText='', regExpObj=None, skipMatches=0,
                      typeName='', fieldName='', replaceText=None,
                      replaceAll=False):
        """Find the search text in the field data and optionally replace it.

        Returns a tuple of the fieldName where found (empty string if not
        found), the node match number and the field match number.
        Returns the last match if skipMatches < 0 (not used with replace).
        Arguments:
            searchText -- the text to find if regExpObj is None
            regExpObj -- the regular expression to find if not None
            skipMatches -- number of already found matches to skip in this node
            typeName -- if given, verify that this node matches this type
            fieldName -- if given, only find matches under this type name
            replaceText -- if not None, replace a match with this string
            replaceAll -- if True, replace all matches (returns last fieldName)
        """
        if typeName and typeName != self.formatRef.name:
            return ('', 0, 0)
        try:
            fields = ([self.formatRef.fieldDict[fieldName]] if fieldName
                      else self.formatRef.fields())
        except KeyError:
            return ('', 0, 0)   # field not in this type
        matchedFieldname = ''
        findCount = 0
        prevFieldFindCount = 0
        for field in fields:
            try:
                fieldText = field.editorText(self)
            except ValueError:
                fieldText = self.data.get(field.name, '')
            fieldFindCount = 0
            pos = 0
            while True:
                if pos >= len(fieldText) and pos > 0:
                    break
                if regExpObj:
                    match = regExpObj.search(fieldText, pos)
                    pos = match.start() if match else -1
                else:
                    pos = fieldText.lower().find(searchText, pos)
                    if not searchText and fieldText:
                        pos = -1  # skip invalid find of empty string
                if pos < 0:
                    break
                findCount += 1
                fieldFindCount += 1
                prevFieldFindCount = fieldFindCount
                matchLen = (len(match.group()) if regExpObj
                            else len(searchText))
                if findCount > skipMatches:
                    matchedFieldname = field.name
                    if replaceText is not None:
                        replace = replaceText
                        if regExpObj:
                            global _origBackrefMatch
                            _origBackrefMatch = match
                            for backrefRe in _replaceBackrefRe:
                                replace = backrefRe.sub(self.replaceBackref,
                                                        replace)
                        fieldText = (fieldText[:pos] + replace +
                                     fieldText[pos + matchLen:])
                        try:
                            self.setData(field, fieldText)
                        except ValueError:
                            pass
                    if not replaceAll and skipMatches >= 0:
                        return (field.name, findCount, fieldFindCount)
                pos = pos + matchLen if matchLen else pos + 1
        if not matchedFieldname:
            findCount = prevFieldFindCount = 0
        return (matchedFieldname, findCount, prevFieldFindCount)

    @staticmethod
    def replaceBackref(match):
        """Return the re match group from _origBackrefMatch for replacement.

        Used for reg exp backreference replacement.
        Arguments:
            match -- the backref match in the replacement string
        """
        return _origBackrefMatch.group(int(match.group(1)))

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
        newNode.addSpotRef(self)
        if newTitle and not newNode.title():
            newNode.setTitle(newTitle)
        treeStructure.addNodeDictRef(newNode)
        return newNode

    def changeParent(self, oldParentSpot, newParentSpot, newPos=-1):
        """Move this node from oldParent to newParent.

        Used for indent and unindent commands.
        Arguments:
            oldParent -- the original parent spot
            newParent -- the new parent spot
            newPos -- the position in the new childList, -1 for append
        """
        oldParent = oldParentSpot.nodeRef
        oldParent.childList.remove(self)
        newParent = newParentSpot.nodeRef
        if newPos >= 0:
            newParent.childList.insert(newPos, self)
        else:
            newParent.childList.append(self)
        # preserve one spot to maintain tree expand state
        self.matchedSpot(oldParentSpot).parentSpot = newParentSpot
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

    def loadChildNodeLevels(self, nodeList, initLevel=-1):
        """Recursively add children from a list of nodes and levels.

        Return True on success, False if data levels are not valid.
        Arguments:
            nodeList -- list of tuples with node and level
            initLevel -- the level of this node in the structure
        """
        while nodeList:
            child, level = nodeList[0]
            if level == initLevel + 1:
                del nodeList[0]
                self.childList.append(child)
                if not child.loadChildNodeLevels(nodeList, level):
                    return False
            else:
                return -1 < level <= initLevel
        return True

    def fieldSortKey(self, level=0):
        """Return a key used to sort by key fields.

        Arguments:
            level -- the sort key depth level for the current sort stage
        """
        if len(self.formatRef.sortFields) > level:
            return self.formatRef.sortFields[level].sortKey(self)
        return ('',)

    def sortChildrenByField(self, recursive=True, forward=True):
        """Sort child nodes by predefined field keys.

        Arguments:
            recursive -- continue to sort recursively if true
            forward -- reverse the sort if false
        """
        formats = set([child.formatRef for child in self.childList])
        maxDepth = 0
        directions = []
        for nodeFormat in formats:
            if not nodeFormat.sortFields:
                nodeFormat.loadSortFields()
            maxDepth = max(maxDepth, len(nodeFormat.sortFields))
            newDirections = [field.sortKeyForward for field in
                             nodeFormat.sortFields]
            directions = [sum(i) for i in itertools.zip_longest(directions,
                                                                newDirections,
                                                                fillvalue=
                                                                False)]
        if forward:
            directions = [bool(direct) for direct in directions]
        else:
            directions = [not bool(direct) for direct in directions]
        for level in range(maxDepth, 0, -1):
            self.childList.sort(key = operator.methodcaller('fieldSortKey',
                                                            level - 1),
                                reverse = not directions[level - 1])
        if recursive:
            for child in self.childList:
                child.sortChildrenByField(True, forward)

    def titleSortKey(self):
        """Return a key used to sort by titles.
        """
        return self.title().lower()

    def sortChildrenByTitle(self, recursive=True, forward=True):
        """Sort child nodes by titles.

        Arguments:
            recursive -- continue to sort recursively if true
            forward -- reverse the sort if false
        """
        self.childList.sort(key = operator.methodcaller('titleSortKey'),
                            reverse = not forward)
        if recursive:
            for child in self.childList:
                child.sortChildrenByTitle(True, forward)

    def updateNodeMathFields(self, treeFormats):
        """Recalculate math fields that depend on this node and so on.

        Return True if any data was changed.
        Arguments:
            treeFormats -- a ref to all of the formats
        """
        changed = False
        for field in self.formatRef.fields():
            for fieldRef in treeFormats.mathFieldRefDict.get(field.name, []):
                for node in fieldRef.dependentEqnNodes(self):
                    if node.recalcMathField(fieldRef.eqnFieldName,
                                            treeFormats):
                        changed = True
        return changed

    def recalcMathField(self, eqnFieldName, treeFormats):
        """Recalculate a math field, if changed, recalc depending math fields.

        Return True if any data was changed.
        Arguments:
            eqnFieldName -- the equation field in this node to update
            treeFormats -- a ref to all of the formats
        """
        changed = False
        oldValue = self.data.get(eqnFieldName, '')
        newValue = self.formatRef.fieldDict[eqnFieldName].equationValue(self)
        if newValue != oldValue:
            self.data[eqnFieldName] = newValue
            changed = True
            for fieldRef in treeFormats.mathFieldRefDict.get(eqnFieldName, []):
                for node in fieldRef.dependentEqnNodes(self):
                    node.recalcMathField(fieldRef.eqnFieldName, treeFormats)
        return changed

    def updateNumbering(self, fieldDict, currentSequence, levelLimit,
                        completedClones, includeRoot=True, reserveNums=True,
                        restartSetting=False):
        """Add auto incremented numbering to fields by type in the dict.

        Arguments:
            fieldDict -- numbering field name lists stored by type name
            currentSequence -- a list of int for the current numbering sequence
            levelLimit -- the number of child levels to include
            completedClones -- set of clone nodes already numbered
            includeRoot -- if Ture, number the current node
            reserveNums -- if true, increment number even without num field
            restartSetting -- if true, restart numbering after a no-field gap
        """
        childSequence = currentSequence[:]
        if includeRoot:
            for fieldName in fieldDict.get(self.formatRef.name, []):
                self.data[fieldName] = '.'.join((repr(num) for num in
                                                 currentSequence))
            if self.formatRef.name in fieldDict or reserveNums:
                childSequence += [1]
                currentSequence[-1] += 1
            if restartSetting and self.formatRef.name not in fieldDict:
                currentSequence[-1] = 1
            if len(self.spotRefs) > 1:
                completedClones.add(self.uId)
        if levelLimit > 0:
            for child in self.childList:
                if len(child.spotRefs) > 1 and child.uId in completedClones:
                    return
                child.updateNumbering(fieldDict, childSequence, levelLimit - 1,
                                      completedClones, True, reserveNums,
                                      restartSetting)

    def isIdentical(self, node, checkParents=True):
        """Return True if node format, data and descendants are identical.

        Also returns False if checkParents & the nodes have parents in common.
        Arguments:
            node -- the node to check
        """
        if (self.formatRef != node.formatRef or
            len(self.childList) != len(node.childList) or
            self.data != node.data or
            (checkParents and not self.parents().isdisjoint(node.parents()))):
            return False
        for thisChild, otherChild in zip(self.childList, node.childList):
            if not thisChild.isIdentical(otherChild, False):
                return False
        return True

    def flatChildCategory(self, origFormats, structure):
        """Collapse descendant nodes by merging fields.

        Overwrites data in any fields with the same name.
        Arguments:
            origFormats -- copy of tree formats before any changes
            structure -- a ref to the tree structure
        """
        thisSpot = self.spotByNumber(0)
        newChildList = []
        for spot in thisSpot.spotDescendantOnlyGen():
            if not spot.nodeRef.childList:
                oldParentSpot = spot.parentSpot
                while oldParentSpot != thisSpot:
                    for field in origFormats[oldParentSpot.nodeRef.formatRef.
                                             name].fields():
                        data = oldParentSpot.nodeRef.data.get(field.name, '')
                        if data:
                            spot.nodeRef.data[field.name] = data
                        spot.nodeRef.formatRef.addFieldIfNew(field.name,
                                                            field.formatData())
                    oldParentSpot = oldParentSpot.parentSpot
                spot.parentSpot = thisSpot
                newChildList.append(spot.nodeRef)
            else:
                structure.removeNodeDictRef(spot.nodeRef)
        self.childList = newChildList

    def addChildCategory(self, catList, structure):
        """Insert category nodes above children.

        Arguments:
            catList -- the field names to add to the new level
            structure -- a ref to the tree structure
        """
        newFormat = None
        catSet = set(catList)
        similarFormats = [nodeFormat for nodeFormat in
                          structure.treeFormats.values() if
                          catSet.issubset(set(nodeFormat.fieldNames()))]
        if similarFormats:
            similarFormat = min(similarFormats, key=lambda f: len(f.fieldDict))
            if len(similarFormat.fieldDict) < len(self.childList[0].
                                                  formatRef.fieldDict):
                newFormat = similarFormat
        if not newFormat:
            newFormatName = '{0}_TYPE'.format(catList[0].upper())
            num = 1
            while newFormatName in structure.treeFormats:
                newFormatName = '{0}_TYPE_{1}'.format(catList[0].upper(), num)
                num += 1
            newFormat = nodeformat.NodeFormat(newFormatName,
                                              structure.treeFormats)
            newFormat.addFieldList(catList, True, True)
            structure.treeFormats[newFormatName] = newFormat
        newParents = []
        for child in self.childList:
            newParent = child.findEqualFields(catList, newParents)
            if not newParent:
                newParent = TreeNode(newFormat)
                for field in catList:
                    data = child.data.get(field, '')
                    if data:
                        newParent.data[field] = data
                structure.addNodeDictRef(newParent)
                newParents.append(newParent)
            newParent.childList.append(child)
        self.childList = newParents
        for child in self.childList:
            child.removeInvalidSpotRefs(True, True)
            child.addSpotRef(self)

    def findEqualFields(self, fieldNames, nodes):
        """Return first node in nodes with same data in fieldNames as self.

        Arguments:
            fieldNames -- the list of fields to check
            nodes -- the nodes to search for a match
        """
        for node in nodes:
            for field in fieldNames:
                if self.data.get(field, '') != node.data.get(field, ''):
                    break
            else:   # this for loop didn't hit break, so we have a match
                return node

    def exportTitleText(self, level=0):
        """Return a list of tabbed title lines for this node and descendants.

        Arguments:
            level -- indicates the indent level needed
        """
        textList = ['\t' * level + self.title()]
        for child in self.childList:
            textList.extend(child.exportTitleText(level + 1))
        return textList
