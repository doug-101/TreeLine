#!/usr/bin/env python3

#******************************************************************************
# breadcrumbview.py, provides a class for the breadcrumb view
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
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextBrowser
import globalref


class CrumbItem:
    """Class to store breadcrumb item spot refs and positions.
    """
    def __init__(self, spotRef):
        """Initialize the breadcrumb item.

        Arguments:
            spotRef -- ref to the associated spot item
        """
        self.spot = spotRef
        self.spotIndex = 0  # index number of this spot in its node
        self.rowSpan = 1  # number of rows to span for same upsteam spot
        self.lastSpot = False  # True for last spot in the chain
        self.selectedSpot = False

    def tableText(self):
        """Return the html needed for the table entry.
        """
        if self.rowSpan == 0:
            return ''
        text = ('<td rowspan="{0}" align="center" valign="middle">{1}</td>'.
                format(self.rowSpan, self.spot.nodeRef.title()))
        if not self.lastSpot:
            # add arrow
            text += ('<td rowspan="{0}" align="center" valign="middle">'
                     '&#x25ba;</td>'.format(self.rowSpan))
        return text


class BreadcrumbView(QTextBrowser):
    """Class override for the breadcrumb view.

    Sets view defaults and updates the content.
    """
    def __init__(self, treeView, parent=None):
        """Initialize the breadcrumb view.

        Arguments:
            treeView - the tree view, needed for the current selection model
            parent -- the parent main window
        """
        super().__init__(parent)
        self.treeView = treeView
        self.setFocusPolicy(Qt.NoFocus)

    def updateContents(self):
        """Reload the view's content if the view is shown.

        Avoids update if view is not visible or has zero height or width.
        """
        selModel = self.treeView.selectionModel()
        selNodes = selModel.selectedNodes()
        if len(selNodes) != 1:
            self.clear()
            return
        spotList = sorted(list(selNodes[0].spotRefs),
                          key=operator.methodcaller('sortKey',
                                                    selModel.modelRef))
        chainList = [[CrumbItem(chainSpot) for chainSpot in spot.spotChain()]
                     for spot in spotList]
        for row in range(len(chainList)):
            for col in range(len(chainList[row])):
                item = chainList[row][col]
                if (row and col < len(chainList[row - 1]) and
                    item.spot is chainList[row - 1][col].spot):
                    item.rowSpan = 0
                else:
                    while (row + item.rowSpan < len(chainList) and
                           col < len(chainList[row + item.rowSpan]) and
                           item.spot is
                           chainList[row + item.rowSpan][col].spot):
                        item.rowSpan += 1
                if col == len(chainList[row]) - 1:
                    item.lastSpot = True
        htmlList = ['<html><body><table border="1" cellpadding="5"'
                    'cellspacing="0">']
        for chain in chainList:
            htmlList.append('<tr>')
            for item in chain:
                htmlList.append(item.tableText())
            htmlList.append('</tr>')
        htmlList.append('</table></body></html>')
        self.setHtml(''.join(htmlList))

    def setSource(self, url):
        """Called when a user clicks on a URL link.

        Selects an internal link or opens an external browser.
        Arguments:
            url -- the QUrl that is clicked
        """
        name = url.toString()
        if name.startswith('#'):
            if not self.selectModel.selectNodeById(name[1:]):
                super().setSource(url)
        else:
            if urltools.isRelative(name):    # check for relative path
                defaultPath = globalref.mainControl.defaultFilePath(True)
                name = urltools.toAbsolute(name, defaultPath)
            dataeditors.openExtUrl(name)

    def hasSelectedText(self):
        """Return True if text is selected.
        """
        return self.textCursor().hasSelection()

    def contextMenuEvent(self, event):
        """Add a popup menu for select all and copy actions.

        Arguments:
            event -- the menu event
        """
        menu = self.createStandardContextMenu()
        menu.removeAction(menu.actions()[1]) #remove copy link location
        menu.exec_(event.globalPos())

    def resizeEvent(self, event):
        """Update view if was collaped by splitter.
        """
        if ((event.oldSize().height() == 0 and event.size().height()) or
            (event.oldSize().width() == 0 and event.size().width())):
            self.updateContents()
        return super().resizeEvent(event)
