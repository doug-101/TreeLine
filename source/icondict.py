#!/usr/bin/env python3

#******************************************************************************
# icondict.py, provides a class to load and store icons
#
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import os.path
from PyQt5.QtGui import QIcon, QPixmap

_iconExtension = ('.png', '.bmp', '.ico', '.gif')
defaultName = 'default'
noneName = 'NoIcon'

class IconDict(dict):
    """Loads and stores icons by name.
    """
    def __init__(self, potentialPaths, subPaths=None):
        """Set icon paths and initialize variables.

        The first potential path that has icons is used.
        Arguments:
            potentialPaths -- a list of path names to check for icons
            subPaths -- a list of optional subpaths under the base paths
        """
        super().__init__()
        self.pathList = []
        self.subPaths = ['']
        self.addIconPath(potentialPaths, subPaths)
        self.allLoaded = False
        self[noneName] = None

    def addIconPath(self, potentialPaths, subPaths=None):
        """Add an icon path and set the subPaths if given.

        Arguments:
            potentialPaths -- a list of path names to check for icons
            subPaths -- a list of optional subpaths under the base paths
        """
        if subPaths:
            self.subPaths = subPaths
        for path in potentialPaths:
            for subPath in self.subPaths:
                try:
                    for name in os.listdir(os.path.join(path, subPath)):
                        pixmap = QPixmap(os.path.join(path, subPath,
                                               name))
                        if not pixmap.isNull():
                            if path not in self.pathList:
                                self.pathList.append(path)
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
        for path in self.pathList:
            for ext in _iconExtension:
                fileName = name + ext
                for subPath in self.subPaths:
                    pixmap = QPixmap(os.path.join(path, subPath,
                                                        fileName))
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
        for path in self.pathList:
            for subPath in self.subPaths:
                try:
                    for name in os.listdir(os.path.join(path, subPath)):
                        pixmap = QPixmap(os.path.join(path, subPath,
                                                            name))
                        if not pixmap.isNull():
                            name = os.path.splitext(name)[0]
                            try:
                                icon = self[name]
                            except KeyError:
                                icon = QIcon()
                                self[name] = icon
                            icon.addPixmap(pixmap)
                except OSError:
                    pass
        self.allLoaded = True
