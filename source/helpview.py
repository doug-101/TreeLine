#!/usr/bin/env python3

#****************************************************************************
# helpview.py, provides a window for viewing an html help file
#
# Copyright (C) 2025, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#*****************************************************************************

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import (QAction, QTextDocument)
from PyQt6.QtWidgets import (QLabel, QLineEdit, QMainWindow, QMenu,
                             QStatusBar, QTextBrowser)
import dataeditors


class HelpView(QMainWindow):
    """Main window for viewing an html help file.
    """
    def __init__(self, pathObj, caption, icons, parent=None):
        """Helpview initialize with text.

        Arguments:
            pathObj -- a path object for the help file
            caption -- the window caption
            icons -- dict of view icons
        """
        QMainWindow.__init__(self, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setStatusBar(QStatusBar())
        self.textView = HelpViewer(self)
        self.setCentralWidget(self.textView)
        self.textView.setSearchPaths([str(pathObj.parent)])
        self.textView.setSource(QUrl(pathObj.as_uri()))
        self.resize(520, 440)
        self.setWindowTitle(caption)
        tools = self.addToolBar(_('Tools'))
        self.menu = QMenu(self.textView)
        self.textView.highlighted.connect(self.showLink)

        backAct = QAction(_('&Back'), self)
        backAct.setIcon(icons['helpback'])
        tools.addAction(backAct)
        self.menu.addAction(backAct)
        backAct.triggered.connect(self.textView.backward)
        backAct.setEnabled(False)
        self.textView.backwardAvailable.connect(backAct.setEnabled)

        forwardAct = QAction(_('&Forward'), self)
        forwardAct.setIcon(icons['helpforward'])
        tools.addAction(forwardAct)
        self.menu.addAction(forwardAct)
        forwardAct.triggered.connect(self.textView.forward)
        forwardAct.setEnabled(False)
        self.textView.forwardAvailable.connect(forwardAct.setEnabled)

        homeAct = QAction(_('&Home'), self)
        homeAct.setIcon(icons['helphome'])
        tools.addAction(homeAct)
        self.menu.addAction(homeAct)
        homeAct.triggered.connect(self.textView.home)

        tools.addSeparator()
        tools.addSeparator()
        findLabel = QLabel(_(' Find: '), self)
        tools.addWidget(findLabel)
        self.findEdit = QLineEdit(self)
        tools.addWidget(self.findEdit)
        self.findEdit.textEdited.connect(self.findTextChanged)
        self.findEdit.returnPressed.connect(self.findNext)

        self.findPreviousAct = QAction(_('Find &Previous'), self)
        self.findPreviousAct.setIcon(icons['helpprevious'])
        tools.addAction(self.findPreviousAct)
        self.menu.addAction(self.findPreviousAct)
        self.findPreviousAct.triggered.connect(self.findPrevious)
        self.findPreviousAct.setEnabled(False)

        self.findNextAct = QAction(_('Find &Next'), self)
        self.findNextAct.setIcon(icons['helpnext'])
        tools.addAction(self.findNextAct)
        self.menu.addAction(self.findNextAct)
        self.findNextAct.triggered.connect(self.findNext)
        self.findNextAct.setEnabled(False)

    def showLink(self, url):
        """Send link text to the statusbar.

        Arguments:
            url -- the QUrl link to show
        """
        self.statusBar().showMessage(url.toString())

    def findTextChanged(self, text):
        """Update find controls based on text in text edit.

        Arguments:
            text -- the search text
        """
        self.findPreviousAct.setEnabled(len(text) > 0)
        self.findNextAct.setEnabled(len(text) > 0)

    def findPrevious(self):
        """Command to find the previous string.
        """
        if self.textView.find(self.findEdit.text(),
                              QTextDocument.FindFlag.FindBackward):
            self.statusBar().clearMessage()
        else:
            self.statusBar().showMessage(_('Text string not found'))

    def findNext(self):
        """Command to find the next string.
        """
        if self.textView.find(self.findEdit.text()):
            self.statusBar().clearMessage()
        else:
            self.statusBar().showMessage(_('Text string not found'))


class HelpViewer(QTextBrowser):
    """Shows an html help file.
    """
    def __init__(self, parent=None):
        """Initialize the viewer.

        Arguments:
            parent -- the parent widget, if given
        """
        QTextBrowser.__init__(self, parent)

    def doSetSource(self, url, resType):
        """Called when user clicks on a URL.

        Arguments:
            url -- the clicked on QUrl
        """
        name = url.toString()
        if name.startswith('http'):
            dataeditors.openExtUrl(name)
        else:
            super().doSetSource(url, resType)

    def contextMenuEvent(self, event):
        """Init popup menu on right click"".

        Arguments:
            event -- the menu event
        """
        self.parentWidget().menu.exec(event.globalPos())
