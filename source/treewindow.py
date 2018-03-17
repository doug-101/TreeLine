#!/usr/bin/env python3

#******************************************************************************
# treewindow.py, provides a class for the main window and controls
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import pathlib
import base64
from PyQt5.QtCore import QEvent, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QGuiApplication, QTextDocument
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QMainWindow,
                             QSplitter, QStackedWidget, QStatusBar, QTabWidget)
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
        self.winActions = {}
        self.toolbars = []
        self.rightTabActList = []
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(True)
        self.setStatusBar(QStatusBar())
        self.setCaption()
        self.setupActions()
        self.setupMenus()
        self.setupToolbars()
        self.restoreToolbarPosition()

        self.treeView = treeview.TreeView(model, self.allActions)
        self.breadcrumbSplitter = QSplitter(Qt.Vertical)
        self.setCentralWidget(self.breadcrumbSplitter)
        self.breadcrumbView = breadcrumbview.BreadcrumbView(self.treeView)
        self.breadcrumbSplitter.addWidget(self.breadcrumbView)
        self.breadcrumbView.setVisible(globalref.
                                       genOptions['InitShowBreadcrumb'])

        self.treeSplitter = QSplitter()
        self.breadcrumbSplitter.addWidget(self.treeSplitter)
        self.treeStack = QStackedWidget()
        self.treeSplitter.addWidget(self.treeStack)
        self.treeStack.addWidget(self.treeView)
        self.treeView.shortcutEntered.connect(self.execShortcut)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                              updateRightViews)
        self.treeFilterView = None

        self.rightTabs = QTabWidget()
        self.treeSplitter.addWidget(self.rightTabs)
        self.rightTabs.setTabPosition(QTabWidget.South)
        self.rightTabs.tabBar().setFocusPolicy(Qt.NoFocus)

        self.outputSplitter = QSplitter(Qt.Vertical)
        self.rightTabs.addTab(self.outputSplitter, _('Data Output'))
        parentOutputView = outputview.OutputView(self.treeView, False)
        parentOutputView.highlighted[str].connect(self.statusBar().showMessage)
        self.outputSplitter.addWidget(parentOutputView)
        childOutputView = outputview.OutputView(self.treeView, True)
        childOutputView.highlighted[str].connect(self.statusBar().showMessage)
        self.outputSplitter.addWidget(childOutputView)

        self.editorSplitter = QSplitter(Qt.Vertical)
        self.rightTabs.addTab(self.editorSplitter, _('Data Edit'))
        parentEditView = dataeditview.DataEditView(self.treeView,
                                                   self.allActions, False)
        parentEditView.shortcutEntered.connect(self.execShortcut)
        parentEditView.focusOtherView.connect(self.focusNextView)
        parentEditView.inLinkSelectMode.connect(self.treeView.
                                                toggleNoMouseSelectMode)
        self.treeView.skippedMouseSelect.connect(parentEditView.
                                                 internalLinkSelected)
        self.editorSplitter.addWidget(parentEditView)
        childEditView = dataeditview.DataEditView(self.treeView,
                                                  self.allActions, True)
        childEditView.shortcutEntered.connect(self.execShortcut)
        childEditView.focusOtherView.connect(self.focusNextView)
        childEditView.inLinkSelectMode.connect(self.treeView.
                                               toggleNoMouseSelectMode)
        self.treeView.skippedMouseSelect.connect(childEditView.
                                                 internalLinkSelected)
        parentEditView.hoverFocusActive.connect(childEditView.endEditor)
        childEditView.hoverFocusActive.connect(parentEditView.endEditor)
        parentEditView.inLinkSelectMode.connect(childEditView.
                                                updateInLinkSelectMode)
        childEditView.inLinkSelectMode.connect(parentEditView.
                                               updateInLinkSelectMode)
        self.editorSplitter.addWidget(childEditView)

        self.titleSplitter = QSplitter(Qt.Vertical)
        self.rightTabs.addTab(self.titleSplitter, _('Title List'))
        parentTitleView = titlelistview.TitleListView(self.treeView, False)
        parentTitleView.shortcutEntered.connect(self.execShortcut)
        self.titleSplitter.addWidget(parentTitleView)
        childTitleView = titlelistview.TitleListView(self.treeView, True)
        childTitleView.shortcutEntered.connect(self.execShortcut)
        self.titleSplitter.addWidget(childTitleView)

        self.rightTabs.currentChanged.connect(self.updateRightViews)
        self.updateFonts()

    def setExternalSignals(self):
        """Connect widow object signals to signals in this object.

        In a separate method to refresh after local control change.
        """
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                                selectChanged)
        for i in range(2):
            self.editorSplitter.widget(i).nodeModified.connect(self.
                                                               nodeModified)
            self.titleSplitter.widget(i).nodeModified.connect(self.
                                                              nodeModified)
            self.titleSplitter.widget(i).treeModified.connect(self.
                                                              treeModified)

    def updateActions(self, allActions):
        """Use new actions for menus, etc. when the local control changes.

        Arguments:
            allActions -- a dict containing the upper level actions
        """
        # remove submenu actions that are children of the window
        self.removeAction(self.allActions['DataNodeType'])
        self.removeAction(self.allActions['FormatFontSize'])
        self.allActions = allActions.copy()
        self.allActions.update(self.winActions)
        self.menuBar().clear()
        self.setupMenus()
        self.addToolbarCommands()
        self.treeView.allActions = self.allActions
        for i in range(2):
            self.editorSplitter.widget(i).allActions = self.allActions

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

    def updateRightViews(self, *args, outputOnly=False):
        """Update all right-hand views and breadcrumb view.

        Arguments:
            *args -- dummy arguments to collect args from signals
            outputOnly -- only update output views (not edit views)
        """
        if globalref.mainControl.activeControl:
            self.rightTabActList[self.rightTabs.
                                 currentIndex()].setChecked(True)
            self.breadcrumbView.updateContents()
            splitter = self.rightTabs.currentWidget()
            if not outputOnly or isinstance(splitter.widget(0),
                                            outputview.OutputView):
                for i in range(2):
                    splitter.widget(i).updateContents()

    def refreshDataEditViews(self):
        """Refresh the data in non-selected cells in curreent data edit views.
        """
        splitter = self.rightTabs.currentWidget()
        if isinstance(splitter.widget(0), dataeditview.DataEditView):
            for i in range(2):
                splitter.widget(i).updateUnselectedCells()

    def updateCommandsAvail(self):
        """Set window commands available based on node selections.
        """
        self.allActions['ViewPrevSelect'].setEnabled(len(self.treeView.
                                                         selectionModel().
                                                         prevSpots) > 1)
        self.allActions['ViewNextSelect'].setEnabled(len(self.treeView.
                                                         selectionModel().
                                                         nextSpots) > 0)

    def updateWinGenOptions(self):
        """Update tree and data edit windows based on general option changes.
        """
        self.treeView.updateTreeGenOptions()
        for i in range(2):
            self.editorSplitter.widget(i).setMouseTracking(globalref.
                                                   genOptions['EditorOnHover'])

    def updateFonts(self):
        """Update custom fonts in views.
        """
        treeFont = QTextDocument().defaultFont()
        treeFontName = globalref.miscOptions['TreeFont']
        if treeFontName:
            treeFont.fromString(treeFontName)
        self.treeView.setFont(treeFont)
        self.treeView.updateTreeGenOptions()
        if self.treeFilterView:
            self.treeFilterView.setFont(treeFont)
        ouputFont = QTextDocument().defaultFont()
        ouputFontName = globalref.miscOptions['OutputFont']
        if ouputFontName:
            ouputFont.fromString(ouputFontName)
        editorFont = QTextDocument().defaultFont()
        editorFontName = globalref.miscOptions['EditorFont']
        if editorFontName:
            editorFont.fromString(editorFontName)
        for i in range(2):
            self.outputSplitter.widget(i).setFont(ouputFont)
            self.editorSplitter.widget(i).setFont(editorFont)
            self.titleSplitter.widget(i).setFont(editorFont)

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

    def filterView(self):
        """Create, show and return a filter view.
        """
        self.removeFilterView()
        self.treeFilterView = treeview.TreeFilterView(self.treeView,
                                                      self.allActions)
        self.treeFilterView.shortcutEntered.connect(self.execShortcut)
        self.treeView.selectionModel().selectionChanged.connect(self.
                                                      treeFilterView.
                                                      updateFromSelectionModel)
        for i in range(2):
            editView = self.editorSplitter.widget(i)
            editView.inLinkSelectMode.connect(self.treeFilterView.
                                              toggleNoMouseSelectMode)
            self.treeFilterView.skippedMouseSelect.connect(editView.
                                                          internalLinkSelected)
        self.treeStack.addWidget(self.treeFilterView)
        self.treeStack.setCurrentWidget(self.treeFilterView)
        return self.treeFilterView

    def removeFilterView(self):
        """Hide and delete the current filter view.
        """
        if self.treeFilterView != None:  # check for None since False if empty
            self.treeStack.removeWidget(self.treeFilterView)
            globalref.mainControl.currentStatusBar().removeWidget(self.
                                                                treeFilterView.
                                                                messageLabel)
            self.treeFilterView.messageLabel.deleteLater()
        self.treeFilterView = None

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

    def execShortcut(self, key):
        """Execute an action based on a shortcut key signal from a view.

        Arguments:
            key -- the QKeySequence shortcut
        """
        keyDict = {action.shortcut().toString(): action for action in
                   self.allActions.values()}
        try:
            action = keyDict[key.toString()]
        except KeyError:
            return
        if action.isEnabled():
            action.trigger()

    def setupActions(self):
        """Add the actions for contols at the window level.

        These actions only affect an individual window,
        they're independent in multiple windows of the same file.
        """
        viewExpandBranchAct = QAction(_('&Expand Full Branch'), self,
                      statusTip=_('Expand all children of the selected nodes'))
        viewExpandBranchAct.triggered.connect(self.viewExpandBranch)
        self.winActions['ViewExpandBranch'] = viewExpandBranchAct

        viewCollapseBranchAct = QAction(_('&Collapse Full Branch'), self,
                    statusTip=_('Collapse all children of the selected nodes'))
        viewCollapseBranchAct.triggered.connect(self.viewCollapseBranch)
        self.winActions['ViewCollapseBranch'] = viewCollapseBranchAct

        viewPrevSelectAct = QAction(_('&Previous Selection'), self,
                          statusTip=_('Return to the previous tree selection'))
        viewPrevSelectAct.triggered.connect(self.viewPrevSelect)
        self.winActions['ViewPrevSelect'] = viewPrevSelectAct

        viewNextSelectAct = QAction(_('&Next Selection'), self,
                       statusTip=_('Go to the next tree selection in history'))
        viewNextSelectAct.triggered.connect(self.viewNextSelect)
        self.winActions['ViewNextSelect'] = viewNextSelectAct

        viewRightTabGrp = QActionGroup(self)
        viewOutputAct = QAction(_('Show Data &Output'), viewRightTabGrp,
                                 statusTip=_('Show data output in right view'),
                                 checkable=True)
        self.winActions['ViewDataOutput'] = viewOutputAct

        viewEditAct = QAction(_('Show Data &Editor'), viewRightTabGrp,
                                 statusTip=_('Show data editor in right view'),
                                 checkable=True)
        self.winActions['ViewDataEditor'] = viewEditAct

        viewTitleAct = QAction(_('Show &Title List'), viewRightTabGrp,
                                  statusTip=_('Show title list in right view'),
                                  checkable=True)
        self.winActions['ViewTitleList'] = viewTitleAct
        self.rightTabActList = [viewOutputAct, viewEditAct, viewTitleAct]
        viewRightTabGrp.triggered.connect(self.viewRightTab)

        viewBreadcrumbAct = QAction(_('Show &Breadcrumb View'), self,
                        statusTip=_('Toggle showing breadcrumb ancestor view'),
                        checkable=True)
        viewBreadcrumbAct.setChecked(globalref.
                                     genOptions['InitShowBreadcrumb'])
        viewBreadcrumbAct.triggered.connect(self.viewBreadcrumb)
        self.winActions['ViewBreadcrumb'] = viewBreadcrumbAct

        viewChildPaneAct = QAction(_('&Show Child Pane'),  self,
                          statusTip=_('Toggle showing right-hand child views'),
                          checkable=True)
        viewChildPaneAct.setChecked(globalref.genOptions['InitShowChildPane'])
        viewChildPaneAct.triggered.connect(self.viewShowChildPane)
        self.winActions['ViewShowChildPane'] = viewChildPaneAct

        viewDescendAct = QAction(_('Show Output &Descendants'), self,
                statusTip=_('Toggle showing output view indented descendants'),
                checkable=True)
        viewDescendAct.setChecked(globalref.genOptions['InitShowDescendants'])
        viewDescendAct.triggered.connect(self.viewDescendants)
        self.winActions['ViewShowDescend'] = viewDescendAct

        winCloseAct = QAction(_('&Close Window'), self,
                                    statusTip=_('Close this window'))
        winCloseAct.triggered.connect(self.close)
        self.winActions['WinCloseWindow'] = winCloseAct

        incremSearchStartAct = QAction(_('Start Incremental Search'), self)
        incremSearchStartAct.triggered.connect(self.incremSearchStart)
        self.addAction(incremSearchStartAct)
        self.winActions['IncremSearchStart'] = incremSearchStartAct

        incremSearchNextAct = QAction(_('Next Incremental Search'), self)
        incremSearchNextAct.triggered.connect(self.incremSearchNext)
        self.addAction(incremSearchNextAct)
        self.winActions['IncremSearchNext'] = incremSearchNextAct

        incremSearchPrevAct = QAction(_('Previous Incremental Search'), self)
        incremSearchPrevAct.triggered.connect(self.incremSearchPrev)
        self.addAction(incremSearchPrevAct)
        self.winActions['IncremSearchPrev'] = incremSearchPrevAct

        for name, action in self.winActions.items():
            icon = globalref.toolIcons.getIcon(name.lower())
            if icon:
                action.setIcon(icon)
            key = globalref.keyboardOptions[name]
            if not key.isEmpty():
                action.setShortcut(key)
        self.allActions.update(self.winActions)

    def setupToolbars(self):
        """Add toolbars based on option settings.
        """
        for toolbar in self.toolbars:
            self.removeToolBar(toolbar)
        self.toolbars = []
        numToolbars = globalref.toolbarOptions['ToolbarQuantity']
        iconSize = globalref.toolbarOptions['ToolbarSize']
        for num in range(numToolbars):
            name = 'Toolbar{:d}'.format(num)
            toolbar = self.addToolBar(name)
            toolbar.setObjectName(name)
            toolbar.setIconSize(QSize(iconSize, iconSize))
            self.toolbars.append(toolbar)
        self.addToolbarCommands()

    def addToolbarCommands(self):
        """Add toolbar commands for current actions.
        """
        for toolbar, commandList in zip(self.toolbars,
                                        globalref.
                                        toolbarOptions['ToolbarCommands']):
            toolbar.clear()
            for command in commandList.split(','):
                if command:
                    try:
                        toolbar.addAction(self.allActions[command])
                    except KeyError:
                        pass
                else:
                    toolbar.addSeparator()


    def setupMenus(self):
        """Add menu items for actions.
        """
        self.fileMenu = self.menuBar().addMenu(_('&File'))
        self.fileMenu.aboutToShow.connect(self.loadRecentMenu)
        self.fileMenu.addAction(self.allActions['FileNew'])
        self.fileMenu.addAction(self.allActions['FileOpen'])
        self.fileMenu.addAction(self.allActions['FileOpenSample'])
        self.fileMenu.addAction(self.allActions['FileImport'])
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.allActions['FileSave'])
        self.fileMenu.addAction(self.allActions['FileSaveAs'])
        self.fileMenu.addAction(self.allActions['FileExport'])
        self.fileMenu.addAction(self.allActions['FileProperties'])
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.allActions['FilePrintSetup'])
        self.fileMenu.addAction(self.allActions['FilePrintPreview'])
        self.fileMenu.addAction(self.allActions['FilePrint'])
        self.fileMenu.addAction(self.allActions['FilePrintPdf'])
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
        dataMenu.addAction(self.allActions['DataCopyType'])
        dataMenu.addSeparator()
        dataMenu.addAction(self.allActions['DataSortNodes'])
        dataMenu.addAction(self.allActions['DataNumbering'])
        dataMenu.addSeparator()
        dataMenu.addAction(self.allActions['DataCloneMatches'])
        dataMenu.addAction(self.allActions['DataDetachClones'])
        dataMenu.addSeparator()
        dataMenu.addAction(self.allActions['DataFlatCategory'])
        dataMenu.addAction(self.allActions['DataAddCategory'])
        dataMenu.addAction(self.allActions['DataSwapCategory'])

        toolsMenu = self.menuBar().addMenu(_('&Tools'))
        toolsMenu.addAction(self.allActions['ToolsFindText'])
        toolsMenu.addAction(self.allActions['ToolsFindCondition'])
        toolsMenu.addAction(self.allActions['ToolsFindReplace'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsFilterText'])
        toolsMenu.addAction(self.allActions['ToolsFilterCondition'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsSpellCheck'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsGenOptions'])
        toolsMenu.addSeparator()
        toolsMenu.addAction(self.allActions['ToolsShortcuts'])
        toolsMenu.addAction(self.allActions['ToolsToolbars'])
        toolsMenu.addAction(self.allActions['ToolsFonts'])

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
        helpMenu.addAction(self.allActions['HelpBasic'])
        helpMenu.addAction(self.allActions['HelpFull'])
        helpMenu.addSeparator()
        helpMenu.addAction(self.allActions['HelpAbout'])

    def viewExpandBranch(self):
        """Expand all children of the selected spots.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        selectedSpots = self.treeView.selectionModel().selectedSpots()
        if not selectedSpots:
            selectedSpots = self.treeView.model().treeStructure.rootSpots()
        for spot in selectedSpots:
            self.treeView.expandBranch(spot)
        QApplication.restoreOverrideCursor()

    def viewCollapseBranch(self):
        """Collapse all children of the selected spots.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        selectedSpots = self.treeView.selectionModel().selectedSpots()
        if not selectedSpots:
            selectedSpots = self.treeView.model().treeStructure.rootSpots()
        for spot in selectedSpots:
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

    def incremSearchStart(self):
        """Start an incremental title search.
        """
        if not self.treeFilterView:
            self.treeView.setFocus()
            self.treeView.incremSearchStart()

    def incremSearchNext(self):
        """Go to the next match in an incremental title search.
        """
        if not self.treeFilterView:
            self.treeView.incremSearchNext()

    def incremSearchPrev(self):
        """Go to the previous match in an incremental title search.
        """
        if not self.treeFilterView:
            self.treeView.incremSearchPrev()

    def loadRecentMenu(self):
        """Load recent file items to file menu before showing.
        """
        for action in self.fileMenu.actions():
            text = action.text()
            if len(text) > 1 and text[0] == '&' and '0' <= text[1] <= '9':
                self.fileMenu.removeAction(action)
        self.fileMenu.insertActions(self.recentFileSep,
                                    globalref.mainControl.recentFiles.
                                    getActions())

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

    def saveToolbarPosition(self):
        """Save the toolbar position to the toolbar options.
        """
        toolbarPos = base64.b64encode(self.saveState().data()).decode('ascii')
        globalref.toolbarOptions.changeValue('ToolbarPosition', toolbarPos)
        globalref.toolbarOptions.writeFile()

    def restoreToolbarPosition(self):
        """Restore the toolbar position from the toolbar options.
        """
        toolbarPos = globalref.toolbarOptions['ToolbarPosition']
        if toolbarPos:
            self.restoreState(base64.b64decode(bytes(toolbarPos, 'ascii')))

    def dragEnterEvent(self, event):
        """Accept drags of files to this window.

        Arguments:
            event -- the drag event object
        """
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        """Open a file dropped onto this window.

         Arguments:
             event -- the drop event object
        """
        fileList = event.mimeData().urls()
        if fileList:
            path = pathlib.Path(fileList[0].toLocalFile())
            globalref.mainControl.openFile(path, checkModified=True)

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
