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

from PyQt5.QtCore import QEvent, QRect, Qt, pyqtSignal
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QMainWindow,
                             QSplitter, QStatusBar, QTabWidget, QWidget)
import treeview
import breadcrumbview
import outputview
import dataeditview
import titlelistview
import treenode
import globalref


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
        self.rightTabActList = []
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(True)
        self.setStatusBar(QStatusBar())
        self.setCaption()
        self.setupActions()
        self.setupMenus()

        self.treeView = treeview.TreeView(model, self.allActions)
        self.breadcrumbSplitter = QSplitter(Qt.Vertical)
        self.setCentralWidget(self.breadcrumbSplitter)
        self.breadcrumbView = breadcrumbview.BreadcrumbView(self.treeView)
        self.breadcrumbSplitter.addWidget(self.breadcrumbView)
        self.breadcrumbView.setVisible(globalref.
                                       genOptions['InitShowBreadcrumb'])

        self.treeSplitter = QSplitter()
        self.breadcrumbSplitter.addWidget(self.treeSplitter)
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
        self.breadcrumbView.updateContents()

    def updateTree(self):
        """Update the full tree view.
        """
        self.treeView.scheduleDelayedItemsLayout()
        self.breadcrumbView.updateContents()

    def updateRightViews(self):
        """Update all right-hand views and breadcrumb view.
        """
        if globalref.mainControl.activeControl:
            self.rightTabActList[self.rightTabs.
                                 currentIndex()].setChecked(True)
            self.breadcrumbView.updateContents()
            splitter = self.rightTabs.currentWidget()
            for i in range(2):
                splitter.widget(i).updateContents()

    def updateCommandsAvail(self):
        """Set window commands available based on node selections.
        """
        self.allActions['ViewPrevSelect'].setEnabled(len(self.treeView.
                                                         selectionModel().
                                                         prevSpots) > 1)
        self.allActions['ViewNextSelect'].setEnabled(len(self.treeView.
                                                         selectionModel().
                                                         nextSpots) > 0)

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

        viewExpandBranchAct = QAction(_('&Expand Full Branch'), self,
                      statusTip=_('Expand all children of the selected nodes'))
        viewExpandBranchAct.triggered.connect(self.viewExpandBranch)
        winActions['ViewExpandBranch'] = viewExpandBranchAct

        viewCollapseBranchAct = QAction(_('&Collapse Full Branch'), self,
                    statusTip=_('Collapse all children of the selected nodes'))
        viewCollapseBranchAct.triggered.connect(self.viewCollapseBranch)
        winActions['ViewCollapseBranch'] = viewCollapseBranchAct

        viewPrevSelectAct = QAction(_('&Previous Selection'), self,
                          statusTip=_('Return to the previous tree selection'))
        viewPrevSelectAct.triggered.connect(self.viewPrevSelect)
        winActions['ViewPrevSelect'] = viewPrevSelectAct

        viewNextSelectAct = QAction(_('&Next Selection'), self,
                       statusTip=_('Go to the next tree selection in history'))
        viewNextSelectAct.triggered.connect(self.viewNextSelect)
        winActions['ViewNextSelect'] = viewNextSelectAct

        viewRightTabGrp = QActionGroup(self)
        viewOutputAct = QAction(_('Show Data &Output'), viewRightTabGrp,
                                 statusTip=_('Show data output in right view'),
                                 checkable=True)
        winActions['ViewDataOutput'] = viewOutputAct

        viewEditAct = QAction(_('Show Data &Editor'), viewRightTabGrp,
                                 statusTip=_('Show data editor in right view'),
                                 checkable=True)
        winActions['ViewDataEditor'] = viewEditAct

        viewTitleAct = QAction(_('Show &Title List'), viewRightTabGrp,
                                  statusTip=_('Show title list in right view'),
                                  checkable=True)
        winActions['ViewTitleList'] = viewTitleAct
        self.rightTabActList = [viewOutputAct, viewEditAct, viewTitleAct]
        viewRightTabGrp.triggered.connect(self.viewRightTab)

        viewBreadcrumbAct = QAction(_('Show &Breadcrumb View'), self,
                        statusTip=_('Toggle showing breadcrumb ancestor view'),
                        checkable=True)
        viewBreadcrumbAct.setChecked(globalref.
                                     genOptions['InitShowBreadcrumb'])
        viewBreadcrumbAct.triggered.connect(self.viewBreadcrumb)
        winActions['ViewBreadcrumb'] = viewBreadcrumbAct

        viewChildPaneAct = QAction(_('&Show Child Pane'),  self,
                          statusTip=_('Toggle showing right-hand child views'),
                          checkable=True)
        viewChildPaneAct.setChecked(globalref.genOptions['InitShowChildPane'])
        viewChildPaneAct.triggered.connect(self.viewShowChildPane)
        winActions['ViewShowChildPane'] = viewChildPaneAct

        viewDescendAct = QAction(_('Show Output &Descedants'), self,
                statusTip=_('Toggle showing output view indented descendants'),
                checkable=True)
        viewDescendAct.setChecked(globalref.genOptions['InitShowDescendants'])
        viewDescendAct.triggered.connect(self.viewDescendants)
        winActions['ViewShowDescend'] = viewDescendAct

        winCloseAct = QAction(_('&Close Window'), self,
                                    statusTip=_('Close this window'))
        winCloseAct.triggered.connect(self.close)
        winActions['WinCloseWindow'] = winCloseAct

        for name, action in winActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions[name]
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
        editMenu.addAction(self.allActions['EditCut'])
        editMenu.addAction(self.allActions['EditCopy'])
        editMenu.addSeparator()
        editMenu.addAction(self.allActions['EditPaste'])
        editMenu.addAction(self.allActions['EditPastePlain'])
        editMenu.addSeparator()
        editMenu.addAction(self.allActions['EditPasteChild'])
        editMenu.addAction(self.allActions['EditPasteBefore'])
        editMenu.addAction(self.allActions['EditPasteAfter'])
        editMenu.addSeparator()
        editMenu.addAction(self.allActions['EditPasteCloneChild'])
        editMenu.addAction(self.allActions['EditPasteCloneBefore'])
        editMenu.addAction(self.allActions['EditPasteCloneAfter'])

        nodeMenu = self.menuBar().addMenu(_('&Node'))
        nodeMenu.addAction(self.allActions['NodeRename'])
        nodeMenu.addSeparator()
        nodeMenu.addAction(self.allActions['NodeAddChild'])
        nodeMenu.addAction(self.allActions['NodeInsertBefore'])
        nodeMenu.addAction(self.allActions['NodeInsertAfter'])
        nodeMenu.addSeparator()
        nodeMenu.addAction(self.allActions['NodeDelete'])
        nodeMenu.addAction(self.allActions['NodeIndent'])
        nodeMenu.addAction(self.allActions['NodeUnindent'])
        nodeMenu.addSeparator()
        nodeMenu.addAction(self.allActions['NodeMoveUp'])
        nodeMenu.addAction(self.allActions['NodeMoveDown'])
        nodeMenu.addAction(self.allActions['NodeMoveFirst'])
        nodeMenu.addAction(self.allActions['NodeMoveLast'])

        dataMenu = self.menuBar().addMenu(_('&Data'))
        # add action's parent to get the sub-menu
        dataMenu.addMenu(self.allActions['DataNodeType'].parent())
        # add the action to activate the shortcut key
        self.addAction(self.allActions['DataNodeType'])
        dataMenu.addAction(self.allActions['DataConfigType'])

        toolsMenu = self.menuBar().addMenu(_('&Tools'))
        toolsMenu.addAction(self.allActions['ToolsGenOptions'])

        formatMenu = self.menuBar().addMenu(_('Fo&rmat'))
        formatMenu.addAction(self.allActions['FormatBoldFont'])
        formatMenu.addAction(self.allActions['FormatItalicFont'])
        formatMenu.addAction(self.allActions['FormatUnderlineFont'])
        formatMenu.addSeparator()
        # add action's parent to get the sub-menu
        formatMenu.addMenu(self.allActions['FormatFontSize'].parent())
        # add the action to activate the shortcut key
        self.addAction(self.allActions['FormatFontSize'])
        formatMenu.addAction(self.allActions['FormatFontColor'])
        formatMenu.addSeparator()
        formatMenu.addAction(self.allActions['FormatExtLink'])
        formatMenu.addAction(self.allActions['FormatIntLink'])
        formatMenu.addSeparator()
        formatMenu.addAction(self.allActions['FormatSelectAll'])
        formatMenu.addAction(self.allActions['FormatClearFormat'])

        viewMenu = self.menuBar().addMenu(_('&View'))
        viewMenu.addAction(self.allActions['ViewExpandBranch'])
        viewMenu.addAction(self.allActions['ViewCollapseBranch'])
        viewMenu.addSeparator()
        viewMenu.addAction(self.allActions['ViewPrevSelect'])
        viewMenu.addAction(self.allActions['ViewNextSelect'])
        viewMenu.addSeparator()
        viewMenu.addAction(self.allActions['ViewDataOutput'])
        viewMenu.addAction(self.allActions['ViewDataEditor'])
        viewMenu.addAction(self.allActions['ViewTitleList'])
        viewMenu.addSeparator()
        viewMenu.addAction(self.allActions['ViewBreadcrumb'])
        viewMenu.addAction(self.allActions['ViewShowChildPane'])
        viewMenu.addAction(self.allActions['ViewShowDescend'])

        self.windowMenu = self.menuBar().addMenu(_('&Window'))
        self.windowMenu.aboutToShow.connect(self.loadWindowMenu)
        self.windowMenu.addAction(self.allActions['WinNewWindow'])
        self.windowMenu.addAction(self.allActions['WinCloseWindow'])
        self.windowMenu.addSeparator()

        helpMenu = self.menuBar().addMenu(_('&Help'))
        helpMenu.addAction(self.allActions['HelpAbout'])

    def viewExpandBranch(self):
        """Expand all children of the selected spots.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        for spot in self.treeView.selectionModel().selectedSpots():
            self.treeView.expandBranch(spot)
        QApplication.restoreOverrideCursor()

    def viewCollapseBranch(self):
        """Collapse all children of the selected spots.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        for spot in self.treeView.selectionModel().selectedSpots():
            self.treeView.collapseBranch(spot)
        QApplication.restoreOverrideCursor()

    def viewPrevSelect(self):
        """Return to the previous tree selection.
        """
        self.treeView.selectionModel().restorePrevSelect()

    def viewNextSelect(self):
        """Go to the next tree selection in history.
        """
        self.treeView.selectionModel().restoreNextSelect()

    def viewRightTab(self, action):
        """Show the tab in the right-hand view given by action.

        Arguments:
            action -- the action triggered in the action group
        """
        if action == self.allActions['ViewDataOutput']:
            self.rightTabs.setCurrentWidget(self.outputSplitter)
        elif action == self.allActions['ViewDataEditor']:
            self.rightTabs.setCurrentWidget(self.editorSplitter)
        else:
            self.rightTabs.setCurrentWidget(self.titleSplitter)

    def viewBreadcrumb(self, checked):
        """Enable or disable the display of the breadcrumb view.

        Arguments:
            checked -- True if to be shown, False if to be hidden
        """
        self.breadcrumbView.setVisible(checked)
        if checked:
            self.updateRightViews()

    def viewShowChildPane(self, checked):
        """Enable or disable the display of children in a split pane.

        Arguments:
            checked -- True if to be shown, False if to be hidden
        """
        for tabNum in range(3):
            for splitNum in range(2):
                view = self.rightTabs.widget(tabNum).widget(splitNum)
                view.hideChildView = not checked
        self.updateRightViews()

    def viewDescendants(self, checked):
        """Set the output view to show indented descendants if checked.

        Arguments:
            checked -- True if to be shown, False if to be hidden
        """
        self.outputSplitter.widget(1).showDescendants = checked
        self.updateRightViews()

    def loadWindowMenu(self):
        """Load window list items to window menu before showing.
        """
        for action in self.windowMenu.actions():
            text = action.text()
            if len(text) > 1 and text[0] == '&' and '0' <= text[1] <= '9':
                self.windowMenu.removeAction(action)
        self.windowMenu.addActions(globalref.mainControl.windowActions())

    def saveWindowGeom(self):
        """Save window geometry parameters to history options.
        """
        globalref.histOptions.changeValue('WindowXSize', self.width())
        globalref.histOptions.changeValue('WindowYSize', self.height())
        globalref.histOptions.changeValue('WindowXPos', self.geometry().x())
        globalref.histOptions.changeValue('WindowYPos', self.geometry().y())
        try:
            upperWidth, lowerWidth = self.breadcrumbSplitter.sizes()
            crumbPercent = int(100 * upperWidth / (upperWidth + lowerWidth))
            globalref.histOptions.changeValue('CrumbSplitPercent',
                                              crumbPercent)

            leftWidth, rightWidth = self.treeSplitter.sizes()
            treePercent = int(100 * leftWidth / (leftWidth + rightWidth))
            globalref.histOptions.changeValue('TreeSplitPercent', treePercent)
            upperWidth, lowerWidth = self.outputSplitter.sizes()
            outputPercent = int(100 * upperWidth / (upperWidth + lowerWidth))
            globalref.histOptions.changeValue('OutputSplitPercent',
                                              outputPercent)
            upperWidth, lowerWidth = self.editorSplitter.sizes()
            editorPercent = int(100 * upperWidth / (upperWidth + lowerWidth))
            globalref.histOptions.changeValue('EditorSplitPercent',
                                              editorPercent)
            upperWidth, lowerWidth = self.titleSplitter.sizes()
            titlePercent = int(100 * upperWidth / (upperWidth + lowerWidth))
            globalref.histOptions.changeValue('TitleSplitPercent',
                                              titlePercent)
        except ZeroDivisionError:
            pass   # skip if splitter sizes were never set
        tabNum = self.rightTabs.currentIndex()
        globalref.histOptions.changeValue('ActiveRightView', tabNum)

    def restoreWindowGeom(self, offset=0):
        """Restore window geometry from history options.

        Arguments:
            offset -- number of pixels to offset window, down and to right
        """
        rect = QRect(globalref.histOptions['WindowXPos'],
                     globalref.histOptions['WindowYPos'],
                     globalref.histOptions['WindowXSize'],
                     globalref.histOptions['WindowYSize'])
        if rect.x() == -1000 and rect.y() == -1000:
            # let OS position window the first time
            self.resize(rect.size())
        else:
            if offset:
                rect.adjust(offset, offset, offset, offset)
            desktop = QApplication.desktop()
            if desktop.isVirtualDesktop():
                # availRect = desktop.screen().rect() # buggy in windows?
                availRect = (QGuiApplication.screens()[0].
                             availableVirtualGeometry())
            else:
                availRect = desktop.availableGeometry(desktop.primaryScreen())
            rect = rect.intersected(availRect)
            self.setGeometry(rect)
        crumbWidth = int(self.breadcrumbSplitter.width() / 100 *
                         globalref.histOptions['CrumbSplitPercent'])
        self.breadcrumbSplitter.setSizes([crumbWidth,
                                          self.breadcrumbSplitter.width() -
                                          crumbWidth])
        treeWidth = int(self.treeSplitter.width() / 100 *
                        globalref.histOptions['TreeSplitPercent'])
        self.treeSplitter.setSizes([treeWidth,
                                    self.treeSplitter.width() - treeWidth])
        outHeight = int(self.outputSplitter.height() / 100.0 *
                        globalref.histOptions['OutputSplitPercent'])
        self.outputSplitter.setSizes([outHeight,
                                     self.outputSplitter.height() - outHeight])
        editHeight = int(self.editorSplitter.height() / 100.0 *
                         globalref.histOptions['EditorSplitPercent'])
        self.editorSplitter.setSizes([editHeight,
                                    self.editorSplitter.height() - editHeight])
        titleHeight = int(self.titleSplitter.height() / 100.0 *
                          globalref.histOptions['TitleSplitPercent'])
        self.titleSplitter.setSizes([titleHeight,
                                    self.titleSplitter.height() - titleHeight])
        self.rightTabs.setCurrentIndex(globalref.
                                       histOptions['ActiveRightView'])

    def resetWindowGeom(self):
        """Set all stored window geometry values back to default settings.
        """
        globalref.histOptions.resetToDefaults(['WindowXPos', 'WindowYPos',
                                               'WindowXSize', 'WindowYSize',
                                               'CrumbSplitPercent',
                                               'TreeSplitPercent',
                                               'OutputSplitPercent',
                                               'EditorSplitPercent',
                                               'TitleSplitPercent',
                                               'ActiveRightView'])

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
