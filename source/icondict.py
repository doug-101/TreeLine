#!/usr/bin/env python3

#******************************************************************************
# icondict.py, provides a class to load and store icons
#
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt5.QtGui import QIcon, QPixmap

_iconExtension = ('.png', '.bmp', '.ico', '.gif')
defaultName = 'default'
noneName = 'NoIcon'

class IconDict(dict):
    """Loads and stores icons by name.
    """
    def __init__(self, pathObjList, subPaths=None):
        """Set icon paths and initialize variables.

        The first potential path that has icons is used.
        Arguments:
            pathObjList -- a list of path objects to check for icons
            subPaths -- a list of optional subpaths under the base paths
        """
        super().__init__()
        self.pathObjList = []
        self.subPaths = ['']
        self.addIconPath(pathObjList, subPaths)
        self.allLoaded = False
        self[noneName] = None

    def addIconPath(self, pathObjList, subPaths=None):
        """Add an icon path and set the subPaths if given.

        Arguments:
            pathObjList -- a list of path objects to check for icons
            subPaths -- a list of optional subpaths under the base paths
        """
        if subPaths:
            self.subPaths = subPaths
        for mainPath in pathObjList:
            for subPath in self.subPaths:
                dirPath = mainPath / subPath
                try:
                    for fullPath in dirPath.iterdir():
                        pixmap = QPixmap(str(fullPath))
                        if not pixmap.isNull():
                            if mainPath not in self.pathObjList:
                                self.pathObjList.append(mainPath)
                            break
                except OSError:
                    pass

    def getIcon(self, name, substitute=False):
        """Return an icon matching the name.

        Load the icon if it isn't already loaded.
        If not found, return None or substitute a default icon.
        Arguments:
            name -- the name of the icon to retrieve
            substitute -- if True, return a default icon if not found
        """
        try:
            icon = self[name]
        except KeyError:
            icon = self.loadIcon(name)
            if not icon and substitute:
                icon = self.getIcon(defaultName)
        return icon

    def loadIcon(self, name):
        """Load an icon from the icon path, add to dict and return the icon.

        Return None if not found.
        Arguments:
            name -- the name of the icon to load
        """
        icon = QIcon()
        for path in self.pathObjList:
            for ext in _iconExtension:
                fileName = name + ext
                for subPath in self.subPaths:
                    pixmap = QPixmap(str(path.joinpath(subPath, fileName)))
                    if not pixmap.isNull():
                        icon.addPixmap(pixmap)
                if not icon.isNull():
                    self[name] = icon
                    return icon
        return None

    def loadIcons(self, nameList):
        """Load icons based on a name list.

        Arguments:
            nameList -- the list of names to load
        """
        for name in nameList:
            self.loadIcon(name)

    def loadAllIcons(self):
        """Load all of the icons available on path list.
        """
        self.clear()
        self[noneName] = None
        for mainPath in self.pathObjList:
            for subPath in self.subPaths:
                dirPath = mainPath / subPath
                try:
                    for fullPath in dirPath.iterdir():
                        pixmap = QPixmap(str(fullPath))
                        if not pixmap.isNull():
                            name = fullPath.stem
                            icon = self.setdefault(name, QIcon())
                            icon.addPixmap(pixmap)
                except OSError:
                    pass
        self.allLoaded = True
