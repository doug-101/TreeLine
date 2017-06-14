#!/usr/bin/env python3

#******************************************************************************
# treeoutput.py, provides classes for output to views, html and printing
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import itertools
import copy
from PyQt5.QtGui import QTextDocument
import globalref


class OutputItem:
    """Class to store output for a single node.

    Stores text lines and original indent level.
    """
    def __init__(self, node, level, addAnchor=False, forceAnchor=False):
        """Convert the node into an output item.

        Arguments:
            node -- the tree node to convert
            level -- the node's original indent level
            addAnchor -- if true, add an ID anchor if node is a link target
            forceAnchor -- if true, add an ID anchor in any case
        """
        nodeFormat = node.formatRef
        if not nodeFormat.useTables:
            self.textLines = [line + '<br />' for line in node.output()]
        else:
            self.textLines = node.output(keepBlanks=True)
        if not self.textLines:
            self.textLines = ['']
        self.addSpace = nodeFormat.spaceBetween
        self.siblingPrefix = nodeFormat.siblingPrefix
        self.siblingSuffix = nodeFormat.siblingSuffix
        if nodeFormat.useBullets and self.textLines:
            # remove <br /> extra space for bullets
            self.textLines[-1] = self.textLines[-1][:-6]
        self.level = level
        # following variables used by printdata only:
        height = 0
        self.pageNum = 0
        self.columnNum = 0
        self.pagePos = 0
        self.doc = None
        self.parentItem = None
        self.lastChildItem = None

    def addIndent(self, prevLevel, nextLevel):
        """Add <div> tags to define indent levels in the output.

        Arguments:
            prevLevel -- the level of the previous item in the list
            nextLevel -- the level of the next item in the list
        """
        for num in range(self.level - prevLevel):
            self.textLines[0] = '<div>' + self.textLines[0]
        for num in range(self.level - nextLevel):
            self.textLines[-1] += '</div>'

    def addAbsoluteIndent(self, pixels):
        """Add tags for an individual indentation.

        Removes the <br /> tag from the last line to avoid excess space,
        since <div> starts a new line.
        The Qt output view does not fully support nested <div> tags.
        Arguments:
            pixels -- the amount to indent
        """
        self.textLines[0] = ('<div style="margin-left: {0}">{1}'.
                             format(pixels * self.level, self.textLines[0]))
        if not self.siblingPrefix and self.textLines[-1].endswith('<br />'):
            self.textLines[-1] = self.textLines[-1][:-6]
        self.textLines[-1] += '</div>'

    def addSiblingPrefix(self):
        """Add the sibling prefix before this output.
        """
        if self.siblingPrefix:
            self.textLines[0] = self.siblingPrefix + self.textLines[0]

    def addSiblingSuffix(self):
        """Add the sibling suffix after this output.
        """
        if self.siblingSuffix:
            self.textLines[-1] += self.siblingSuffix

    def numLines(self):
        """Return the number of text lines in the item.
        """
        return len(self.textLines)

    def equalPrefix(self, otherItem):
        """Return True if sibling prefixes and suffixes are equal.

        Arguments:
            otherItem -- the item to compare
        """
        return (self.siblingPrefix == otherItem.siblingPrefix and
                self.siblingSuffix == otherItem.siblingSuffix)

    def setDocHeight(self, paintDevice, width, printFont,
                          replaceDoc=False):
        """Set the height of this item for use in printer output.

        Creates an output document if not already created.
        Arguments:
            paintDevice -- the printer or other device for settings
            width -- the width available for the output text
            printFont -- the default font for the document
            replaceDoc -- if true, re-create the text document
        """
        if not self.doc or replaceDoc:
            self.doc = QTextDocument()
            lines = '\n'.join(self.textLines)
            if lines.endswith('<br />'):
                # remove trailing <br /> tag to avoid excess space
                lines = lines[:-6]
            self.doc.setHtml(lines)
            self.doc.setDefaultFont(printFont)
            frameFormat = self.doc.rootFrame().frameFormat()
            frameFormat.setBorder(0)
            frameFormat.setMargin(0)
            frameFormat.setPadding(0)
            self.doc.rootFrame().setFrameFormat(frameFormat)
        layout = self.doc.documentLayout()
        layout.setPaintDevice(paintDevice)
        self.doc.setTextWidth(width)
        self.height = layout.documentSize().height()

    def splitDocHeight(self, initHeight, maxHeight, paintDevice, width,
                            printFont):
        """Split this item into two items and return them.

        The first item will fit into initHeight if practical.
        Splits at line endings if posible.
        Arguments:
            initHeight -- the preferred height of the first page
            maxheight -- the max height of any pages
            paintDevice -- the printer or other device for settings
            width -- the width available for the output text
            printFont -- the default font for the document
        """
        newItem = copy.deepcopy(self)
        fullHeight = self.height
        lines = '\n'.join(self.textLines)
        allLines = [line + '<br />' for line in lines.split('<br />')]
        self.textLines = []
        prevHeight = 0
        for line in allLines:
            self.textLines.append(line)
            self.setDocHeight(paintDevice, width, printFont, True)
            if ((prevHeight and self.height > initHeight and
                 fullHeight - prevHeight < maxHeight) or
                (prevHeight and self.height > maxHeight)):
                self.textLines = self.textLines[:-1]
                self.setDocHeight(paintDevice, width, printFont, True)
                newItem.textLines = allLines[len(self.textLines):]
                newItem.setDocHeight(paintDevice, width, printFont, True)
                return (self, newItem)
            if self.height > maxHeight:
                break
            prevHeight = self.height
        # no line ending breaks found
        text = ' \n'.join(allLines)
        allWords = [word + ' ' for word in text.split(' ')]
        newWords = []
        prevHeight = 0
        for word in allWords:
            if word.strip() == '<img':
                break
            newWords.append(word)
            self.textLines = [''.join(newWords)]
            self.setDocHeight(paintDevice, width, printFont, True)
            if ((prevHeight and self.height > initHeight and
                 fullHeight - prevHeight < maxHeight) or
                (prevHeight and self.height > maxHeight)):
                self.textLines = [''.join(newWords[:-1])]
                self.setDocHeight(paintDevice, width, printFont, True)
                newItem.textLines = [''.join(allWords[len(newWords):])]
                newItem.setDocHeight(paintDevice, width, printFont, True)
                return (self, newItem)
            if self.height > maxHeight:
                break
            prevHeight = self.height
        newItem.setDocHeight(paintDevice, width, printFont, True)
        return (newItem, None)   # fail to split


class OutputGroup(list):
    """A list of OutputItems that takes TreeNodes as input.

    Modifies the output text for use in views, html and printing.
    """
    def __init__(self, nodeList, includeRoot=True, includeDescend=False,
                 openOnly=False, addAnchors=False, extraAnchorLevels=0):
        """Convert the node iter list into a list of output items.

        Arguments:
            nodeList -- a list of nodes to convert to output
            includeRoot -- if True, include the nodes in nodeList
            includeDescend -- if True, include children, grandchildren, etc.
            openOnly -- if true, ignore collapsed children in the main treeView
            addAnchors -- if true, add ID anchors to nodes used as link targets
            extraAnchorLevels -- add extra anchors if the level < this
        """
        super().__init__()
        for node in nodeList:
            level = -1
            if includeRoot:
                level = 0
                self.append(OutputItem(node, level, addAnchors,
                                       level < extraAnchorLevels))
            if includeDescend:
                self.addChildren(node, level, openOnly, addAnchors,
                                 extraAnchorLevels)

    def addChildren(self, node, level, openOnly=False, addAnchors=False,
                    extraAnchorLevels=0):
        """Recursively add OutputItems for descendants of the given node.

        Arguments:
            node -- the parent tree node
            level -- the parent node's original indent level
            addAnchors - if true, add ID anchors to nodes used as link targets
            extraAnchorLevels -- add extra anchors if the level < this
        """
        if not openOnly or node.isExpanded():
            for child in node.childList:
                self.append(OutputItem(child, level + 1, addAnchors,
                                       level + 1 < extraAnchorLevels))
                self.addChildren(child, level + 1, openOnly, addAnchors,
                                 extraAnchorLevels)

    def addIndents(self):
        """Add nested <div> elements to define indentations in the output.
        """
        prevLevel = 0
        for item, nextItem in itertools.zip_longest(self, self[1:]):
            try:
                nextLevel = nextItem.level
            except AttributeError:
                nextLevel = 0
            item.addIndent(prevLevel, nextLevel)
            prevLevel = item.level

    def addAbsoluteIndents(self, pixels=20):
        """Add tags for individual indentation on each node.

        The Qt output view does not fully support nested <div> tags.
        Arguments:
            pixels -- the amount to indent
        """
        for item in self:
            item.addAbsoluteIndent(pixels)

    def addBlanksBetween(self):
        """Add blank lines between nodes based on node format's spaceBetween.
        """
        for item, nextItem in zip(self, self[1:]):
            if item.addSpace or nextItem.addSpace:
                item.textLines[-1] += '<br />'

    def hasPrefixes(self):
        """Return True if sibling prefixes or suffixes are found.
        """
        return bool([item for item in self if item.siblingPrefix or
                     item.siblingSuffix])

    def addSiblingPrefixes(self):
        """Add sibling prefixes and suffixes for each node.
        """
        if not self.hasPrefixes():
            return
        addPrefix = True
        for item, nextItem in itertools.zip_longest(self, self[1:]):
            if addPrefix:
                item.addSiblingPrefix()
            if (not nextItem or item.level != nextItem.level or
                not item.equalPrefix(nextItem)):
                item.addSiblingSuffix()
                addPrefix = True
            else:
                addPrefix = False

    def combineAllSiblings(self):
        """Group all sibling items with the same prefix into single items.

        Also add sibling prefixes and suffixes and spaces in between.
        """
        newItems = []
        prevItem = None
        for item in self:
            if prevItem:
                if item.level == prevItem.level and item.equalPrefix(prevItem):
                    if item.addSpace or prevItem.addSpace:
                        prevItem.textLines[-1] += '<br />'
                    prevItem.textLines.extend(item.textLines)
                else:
                    prevItem.addSiblingSuffix()
                    newItems.append(prevItem)
                    item.addSiblingPrefix()
                    prevItem = item
            else:
                item.addSiblingPrefix()
                prevItem = item
        prevItem.addSiblingSuffix()
        newItems.append(prevItem)
        self[:] = newItems

    def combineLines(self, addSpacing=True, addPrefixes=True):
        """Return an OutputItem including all of the text from all items.

        Arguments:
            addPrefixes -- if True, add sibling prefix and suffix to result
            addSpacing -- if True, add spacing between items with addSpace True
        """
        comboItem = copy.deepcopy(self[0])
        for item in self[1:]:
            if item.addSpace:
                comboItem.textLines[-1] += '<br />'
            comboItem.textLines.extend(item.textLines)
        if addPrefixes:
            comboItem.addSiblingPrefix()
            comboItem.addSiblingSuffix()
        return comboItem

    def splitColumns(self, numColumns):
        """Split output into even length columns using number of lines.

       Return a list with a group for each column.
       Arguments:
           numColumns - the number of columns to split
       """
        if numColumns < 2:
            return [self]
        groupList = []
        if len(self) <= numColumns:
            for item in self:
                groupList.append(OutputGroup([]))
                groupList[-1].append(item)
            return groupList
        numEach = len(self) // numColumns
        for colNum in range(numColumns - 1):
            groupList.append(OutputGroup([]))
            groupList[-1].extend(self[colNum * numEach :
                                      (colNum + 1) * numEach])
        groupList.append(OutputGroup([]))
        groupList[-1].extend(self[(numColumns - 1) * numEach : ])
        numChanges = 1
        while numChanges:
            numChanges = 0
            for colNum in range(numColumns - 1):
                if (groupList[colNum].totalNumLines() > groupList[colNum + 1].
                    totalNumLines() + groupList[colNum][-1].numLines()):
                    groupList[colNum + 1].insert(0, groupList[colNum][-1])
                    del groupList[colNum][-1]
                    numChanges += 1
                if (groupList[colNum].totalNumLines() +
                    groupList[colNum + 1][0].numLines() <=
                    groupList[colNum + 1].totalNumLines()):
                    groupList[colNum].append(groupList[colNum + 1][0])
                    del groupList[colNum + 1][0]
                    numChanges += 1
        return groupList

    def getLines(self):
        """Return the full list of text lines from this group.
        """
        if not self:
            return []
        lines = []
        for item in self:
            lines.extend(item.textLines)
        return lines

    def totalNumLines(self):
        """Return the total number of lines of all items in this container.
        """
        return sum([item.numLines() for item in self])

    def loadFamilyRefs(self):
        """Set parentItem and lastChildItem for all items.

        Used by the printdata class.
        """
        recentParents = [None]
        for item in self:
            if item.level > 0:
                item.parentItem = recentParents[item.level - 1]
                item.parentItem.lastChildItem = item
            try:
                recentParents[item.level] = item
            except IndexError:
                recentParents.append(item)
