#!/usr/bin/env python3

#******************************************************************************
# recentfiles.py, classes to save recent file lists, states and actions
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import pathlib
import os
import time
from PyQt5.QtWidgets import QAction
import globalref

_maxActionPathLength = 30
_maxOpenNodesStored = 100


class RecentFileItem:
    """Class containing path, state and action info for a single recent file.
    """
    def __init__(self, pathObj=None, dataDict=None):
        """Initialize with either a pathObject or a stored data dict.

        Arguments:
            pathObj -- a path object for the file
            dataDict -- dict of staore data
        """
        if not dataDict:
            dataDict = {}
        self.pathObj = pathObj
        path = dataDict.get('path', '')
        if not self.pathObj and path:
            self.pathObj = pathlib.Path(path)
        self.stateTime = dataDict.get('time', 0)
        self.scrollPos = dataDict.get('scroll', '')
        self.selectSpots = dataDict.get('select', [])
        self.openSpots = dataDict.get('open', [])

    def dataDict(self):
        """Return the data dict for storing this recent file.
        """
        return {'path': str(self.pathObj), 'time': self.stateTime,
                'scroll': self.scrollPos, 'select': self.selectSpots,
                'open': self.openSpots}

    def pathIsValid(self):
        """Return True if the current path points to an actual file.
        """
        try:
            return self.pathObj.is_file()
        except OSError:
            return False

    def itemAction(self, posNum):
        """Return a menu action for this recent file.

        Arguments:
            posNum -- the position number in the menu
        """
        abbrevPath = str(self.pathObj)
        if len(abbrevPath) > _maxActionPathLength:
            truncLength = _maxActionPathLength - 3
            pos = abbrevPath.find(os.sep, len(abbrevPath) - truncLength)
            if pos < 0:
                pos = len(abbrevPath) - truncLength
            abbrevPath = '...' + abbrevPath[pos:]
        text = '&{0:d} {1}'.format(posNum, abbrevPath)
        action = QAction(text, globalref.mainControl,
                         statusTip=str(self.pathObj))
        action.triggered.connect(self.openFile)
        return action

    def openFile(self):
        """Open this path using the main control method.
        """
        globalref.mainControl.openFile(self.pathObj, checkModified=True)

    def recordTreeState(self, localControl):
        """Save the tree state of this item.

        Arguments:
            localControl -- the control to store
        """
        self.stateTime = int(time.time())
        treeView = localControl.activeWindow.treeView
        topSpot = treeView.spotAtTop()
        self.scrollPos = topSpot.spotId() if topSpot else ''
        self.selectSpots = [spot.spotId() for spot in
                            treeView.selectionModel().selectedSpots()]
        self.openSpots = [spot.spotId() for spot in localControl.structure.
                          spotByNumber(0).expandedSpotDescendantGen(treeView)]
        self.openSpots = self.openSpots[:_maxOpenNodesStored]

    def restoreTreeState(self, localControl):
        """Restore the tree state of this item.

        Arguments:
            localControl -- the control to set state
        """
        fileModTime = self.pathObj.stat().st_mtime
        if self.stateTime == 0 or fileModTime > self.stateTime:
            return    # file modified externally
        treeView = localControl.activeWindow.treeView
        for spotId in self.openSpots:
            treeView.expandSpot(localControl.structure.spotById(spotId))
        if self.scrollPos:
            treeView.scrollToSpot(localControl.structure.
                                  spotById(self.scrollPos))
        if self.selectSpots:
            treeView.selectionModel().selectSpots([localControl.structure.
                                                   spotById(spotId) for spotId
                                                   in self.selectSpots])

    def __eq__(self, other):
        """Test for equality between RecentFileItems and paths.

        Arguments:
            other -- either a RecentFileItem or a path string
        """
        try:
            otherPath = other.pathObj
        except AttributeError:
            otherPath = other
        try:
            return self.pathObj.samefile(otherPath)
        except OSError:
            return False

    def __ne__(self, other):
        """Test for inequality between RecentFileItems and paths.

        Arguments:
            other -- either a RecentFileItem or a path string
        """
        try:
            otherPath = other.pathObj
        except AttributeError:
            otherPath = other
        try:
            return not self.pathObj.samefile(otherPath)
        except OSError:
            return True


class RecentFileList(list):
    """A list of recent file items.
    """
    def __init__(self):
        """Load the initial list from the options file.
        """
        super().__init__()
        self.updateNumEntries()
        for data in globalref.histOptions['RecentFiles']:
            item = RecentFileItem(dataDict=data)
            if item.pathIsValid():
                self.append(item)

    def updateNumEntries(self):
        """Get number of entries value from general options.
        """
        self.numEntries = globalref.genOptions['RecentFiles']

    def writeItems(self):
        """Write the recent items to the options file.
        """
        data = [item.dataDict() for item in self[:self.numEntries]]
        globalref.histOptions.changeValue('RecentFiles', data)

    def addItem(self, pathObj):
        """Add the given path at the start of the list.

        If the path is in the list, move it to the start,
        otherwise create a new item.
        Arguments:
            pathObj -- the new path object to search and/or create
        """
        item = RecentFileItem(pathObj)
        try:
            item = self.pop(self.index(item))
        except ValueError:
            pass
        self.insert(0, item)

    def removeItem(self, pathObj):
        """Remove the given path name if found.

        Arguments:
            pathObj -- the path to be removed
        """
        try:
            self.remove(RecentFileItem(pathObj))
        except ValueError:
            pass

    def getActions(self):
        """Return a list of actions for ech recent item.
        """
        return [item.itemAction(i) for i, item in
                enumerate(self[:self.numEntries], 1)]

    def firstDir(self):
        """Return a path object of the first valid directory from recent items.
        """
        for item in self:
            pathObj = item.pathObj.parent
            try:
                if pathObj.is_dir():
                    return pathObj
            except OSError:
                pass
        return None

    def firstPath(self):
        """Return the first full path from the recent items if valid.
        """
        if self and self[0].pathIsValid():
            return self[0].pathObj
        return None

    def saveTreeState(self, localControl):
        """Save the tree state of the item matching the localControl.

        Arguments:
            localControl -- the control to store
        """
        try:
            item = self[self.index(localControl.filePathObj)]
        except ValueError:
            return
        item.recordTreeState(localControl)

    def retrieveTreeState(self, localControl):
        """Restore the saved tree state of the item matching the localControl.

        Arguments:
            localControl -- the control to restore state
        """
        try:
            item = self[self.index(localControl.filePathObj)]
        except ValueError:
            return
        item.restoreTreeState(localControl)
