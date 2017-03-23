#!/usr/bin/env python3

#******************************************************************************
# treewindow.py, provides a class for the main window and controls
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, QStatusBar,
                             QTabWidget, QWidget)
import treeview
import outputview
import dataeditview
import titlelistview
import treenode


class TreeWindow(QMainWindow):
    """Class override for the main window.

    Contains main window views and controls.
    """
    selectChanged = pyqtSignal()
    nodeModified = pyqtSignal(treenode.TreeNode)
    treeModified = pyqtSignal()
    winActivated = pyqtSignal(QMainWindow)
    winClosing = pyqtSignal(QMainWindow)
    def __init__(self, model, allActions, parent=None):
        """Initialize the main window.

        Arguments:
            model -- the initial data model
            allActions -- a dict containing the upper level actions
            parent -- the parent window, usually None
        """
        super().__init__(parent)
        self.allActions = allActions.copy()
        self.allowCloseFlag = True
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(True)
        self.setStatusBar(QStatusBar())
        self.setCaption()
        self.setupActions()
        self.setupMenus()

        self.breadcrumbSplitter = QSplitter(Qt.Vertical)
        self.setCentralWidget(self.breadcrumbSplitter)
        self.breadcrumbView = QWidget()
        self.breadcrumbSplitter.addWidget(self.breadcrumbView)

        self.treeSplitter = QSplitter()
        self.breadcrumbSplitter.addWidget(self.treeSplitter)
        self.treeView = treeview.TreeView(model, self.allActions)
        self.treeSplitter.addWidget(self.treeView)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                                selectChanged)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                              updateRightViews)

        self.rightTabs = QTabWidget()
        self.treeSplitter.addWidget(self.rightTabs)
        self.rightTabs.setTabPosition(QTabWidget.South)
        self.rightTabs.tabBar().setFocusPolicy(Qt.NoFocus)

        self.outputSplitter = QSplitter(Qt.Vertical)
        self.rightTabs.addTab(self.outputSplitter, _('Data Output'))
        parentOutputView = outputview.OutputView(self.treeView, False)
        self.outputSplitter.addWidget(parentOutputView)
        childOutputView = outputview.OutputView(self.treeView, True)
        self.outputSplitter.addWidget(childOutputView)

        self.editorSplitter = QSplitter(Qt.Vertical)
        self.rightTabs.addTab(self.editorSplitter, _('Data Edit'))
        parentEditView = dataeditview.DataEditView(self.treeView,
                                                   self.allActions, False)
        parentEditView.nodeModified.connect(self.nodeModified)
        parentEditView.focusOtherView.connect(self.focusNextView)
        self.editorSplitter.addWidget(parentEditView)
        childEditView = dataeditview.DataEditView(self.treeView,
                                                  self.allActions, True)
        childEditView.nodeModified.connect(self.nodeModified)
        childEditView.focusOtherView.connect(self.focusNextView)
        self.editorSplitter.addWidget(childEditView)

        self.titleSplitter = QSplitter(Qt.Vertical)
        self.rightTabs.addTab(self.titleSplitter, _('Title List'))
        parentTitleView = titlelistview.TitleListView(self.treeView, False)
        parentTitleView.nodeModified.connect(self.nodeModified)
        parentTitleView.treeModified.connect(self.treeModified)
        self.titleSplitter.addWidget(parentTitleView)
        childTitleView = titlelistview.TitleListView(self.treeView, True)
        childTitleView.nodeModified.connect(self.nodeModified)
        childTitleView.treeModified.connect(self.treeModified)
        self.titleSplitter.addWidget(childTitleView)

        self.rightTabs.currentChanged.connect(self.updateRightViews)

    def updateTreeNode(self, node):
        """Update all spots for the given node in the tree view.

        Arguments:
            node -- the node to be updated
        """
        for spot in node.spotRefs:
            self.treeView.update(spot.index(self.treeView.model()))
        self.treeView.resizeColumnToContents(0)

    def updateTree(self):
        """Update the full tree view.
        """
        self.treeView.scheduleDelayedItemsLayout()

    def updateRightViews(self):
        """Update all right-hand views.
        """
        splitter = self.rightTabs.currentWidget()
        for i in range(2):
            splitter.widget(i).updateContents()

    def resetTreeModel(self, model):
        """Change the model assigned to the tree view.

        Arguments:
            model -- the new model to assign
        """
        self.treeView.resetModel(model)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                              updateRightViews)

    def activateAndRaise(self):
        """Activate this window and raise it to the front.
        """
        self.activateWindow()
        self.raise_()

    def setCaption(self, pathObj=None):
        """Change the window caption title based on the file name and path.

        Arguments:
            pathObj - a path object for the current file
        """
        if pathObj:
            caption = '{0} [{1}] - TreeLine'.format(str(pathObj.name),
                                                    str(pathObj.parent))
        else:
            caption = '- TreeLine'
        self.setWindowTitle(caption)

    def rightParentView(self):
        """Return the current right-hand parent view if visible (or None).
        """
        view = self.rightTabs.currentWidget().widget(0)
        if not view.isVisible() or view.height() == 0 or view.width() == 0:
            return None
        return view

    def rightChildView(self):
        """Return the current right-hand parent view if visible (or None).
        """
        view = self.rightTabs.currentWidget().widget(1)
        if not view.isVisible() or view.height() == 0 or view.width() == 0:
            return None
        return view

    def focusNextView(self, forward=True):
        """Focus the next pane in the tab focus series.

        Called by a signal from the data edit views.
        Tab sequences tend to skip views without this.
        Arguments:
            forward -- forward in tab series if True
        """
        reason = (Qt.TabFocusReason if forward
                  else Qt.BacktabFocusReason)
        rightParent = self.rightParentView()
        rightChild = self.rightChildView()
        if (self.sender().isChildView == forward or
            (forward and rightChild == None) or
            (not forward and rightParent == None)):
            self.treeView.setFocus(reason)
        elif forward:
            rightChild.setFocus(reason)
        else:
            rightParent.setFocus(reason)

    def setupActions(self):
        """Add the actions for contols at the window level.

        These actions only affect an individual window,
        they're independent in multiple windows of the same file.
        """
        winActions = {}

        for name, action in winActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions.getValue(name)
            if not key.isEmpty():
                action.setShortcut(key)
        self.allActions.update(winActions)

    def setupMenus(self):
        """Add menu items for actions.
        """
        self.fileMenu = self.menuBar().addMenu(_('&File'))
        self.fileMenu.addAction(self.allActions['FileNew'])
        self.fileMenu.addAction(self.allActions['FileOpen'])
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.allActions['FileSave'])
        self.fileMenu.addAction(self.allActions['FileSaveAs'])
        self.fileMenu.addSeparator()
        self.recentFileSep = self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.allActions['FileQuit'])

        editMenu = self.menuBar().addMenu(_('&Edit'))
        editMenu.addAction(self.allActions['EditUndo'])
        editMenu.addAction(self.allActions['EditRedo'])
        editMenu.addSeparator()

    def changeEvent(self, event):
        """Detect an activation of the main window and emit a signal.

        Arguments:
            event -- the change event object
        """
        super().changeEvent(event)
        if (event.type() == QEvent.ActivationChange and
            QApplication.activeWindow() == self):
            self.winActivated.emit(self)

    def closeEvent(self, event):
        """Signal that the view is closing and close if the flag allows it.

        Also save window status if necessary.
        Arguments:
            event -- the close event object
        """
        self.winClosing.emit(self)
        if self.allowCloseFlag:
            event.accept()
        else:
            event.ignore()
