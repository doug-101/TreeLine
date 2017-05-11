#!/usr/bin/env python3

#******************************************************************************
# optiondefaults.py, defines defaults for config options
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import options


daysOfWeek = [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'),
              _('Friday'), _('Saturday'), _('Sunday')]


def setGenOptionDefaults(generalOptions):
    """Set defaults for general config options.
    """
    StringOptionItem = options.StringOptionItem
    IntOptionItem = options.IntOptionItem
    BoolOptionItem = options.BoolOptionItem
    ListOptionItem = options.ListOptionItem
    BoolOptionItem(generalOptions, 'AutoFileOpen', False,
                   _('Startup Condition'),
                   _('Automatically open last file used'))
    BoolOptionItem(generalOptions, 'InitShowBreadcrumb', True,
                   _('Startup Condition'),
                   _('Show breadcrumb ancestor view'))
    BoolOptionItem(generalOptions, 'InitShowChildPane', True,
                   _('Startup Condition'),
                   _('Show child pane in right hand views'))
    BoolOptionItem(generalOptions, 'InitShowDescendants', False,
                   _('Startup Condition'),
                   _('Show descendants in output view'))
    BoolOptionItem(generalOptions, 'SaveTreeStates', True,
                   _('Startup Condition'),
                   _('Restore tree view states of recent files'))
    BoolOptionItem(generalOptions, 'SaveWindowGeom', True,
                   _('Startup Condition'),
                   _('Restore previous window geometry'))
    BoolOptionItem(generalOptions, 'OpenNewWindow', True,
                   _('Features Available'),
                   _('Open files in new windows'))
    BoolOptionItem(generalOptions, 'ClickRename', True,
                   _('Features Available'), _('Click node to rename'))
    BoolOptionItem(generalOptions, 'RenameNewNodes', True,
                   _('Features Available'), _('Rename new nodes when created'))
    BoolOptionItem(generalOptions, 'DragTree', True, _('Features Available'),
                   _('Tree drag && drop available'))
    BoolOptionItem(generalOptions, 'ShowTreeIcons', True,
                   _('Features Available'), _('Show icons in the tree view'))
    BoolOptionItem(generalOptions, 'ShowMath', True, _('Features Available'),
                   _('Show math fields in the Data Edit view'))
    BoolOptionItem(generalOptions, 'EditNumbering', False,
                   _('Features Available'),
                   _('Show numbering fields in the Data Edit view'))
    IntOptionItem(generalOptions, 'UndoLevels', 5, 0, 999, _('Undo Memory'),
                  _('Number of undo levels'), 1)
    IntOptionItem(generalOptions, 'AutoSaveMinutes', 0, 0, 999, _('Auto Save'),
                  _('Minutes between saves\n(set to 0 to disable)'), 1)
    IntOptionItem(generalOptions, 'RecentFiles', 4, 0, 99, _('Recent Files'),
                  _('Number of recent files \nin the file menu'), 1)
    StringOptionItem(generalOptions, 'EditTimeFormat', 'H:mm:ss', False, True,
                     _('Data Editor Formats'), _('Times'), 1)
    StringOptionItem(generalOptions, 'EditDateFormat', 'MM/dd/yy', False, True,
                     _('Data Editor Formats'), _('Dates'), 1)
    ListOptionItem(generalOptions, 'WeekStart', daysOfWeek[-1], daysOfWeek,
                   _('Data Editor Formats'), _('First day\nof week'), 1)
    IntOptionItem(generalOptions, 'IndentOffset', 2, 0, 99, _('Appearance'),
                  _('Child indent offset\n(in font height units) '), 1)

def setMiscOptionDefaults(miscOptions):
    """Set defaults for miscellaneous config options.
    """
    StringOptionItem = options.StringOptionItem
    StringOptionItem(miscOptions, 'PrintUnits', 'in', False, True,
                     _('Printer Settings'))
    StringOptionItem(miscOptions, 'SpellCheckPath', '', True, False,
                     _('Spell Check'))
    StringOptionItem(miscOptions, 'TreeFont', '', True, True, _('Fonts'))
    StringOptionItem(miscOptions, 'OutputFont', '', True, True, _('Fonts'))
    StringOptionItem(miscOptions, 'EditorFont', '', True, True, _('Fonts'))

def setHistOptionDefaults(historyOptions):
    """Set defaults for history config options.
    """
    IntOptionItem = options.IntOptionItem
    IntOptionItem(historyOptions, 'WindowXSize', 640, 10, 10000,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'WindowYSize', 640, 10, 10000,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'WindowXPos', -1000, -1000, 10000,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'WindowYPos', -1000, -1000, 10000,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'CrumbSplitPercent', 10, 1, 99,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'TreeSplitPercent', 40, 1, 99,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'OutputSplitPercent', 20, 1, 99,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'EditorSplitPercent', 25, 1, 99,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'TitleSplitPercent', 10, 1, 99,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'ActiveRightView', 0, 0, 2,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'PrintPrevXSize', 0, 0, 10000,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'PrintPrevYSize', 0, 0, 10000,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'PrintPrevXPos', -1000, -1000, 10000,
                  _('Window Geometry'))
    IntOptionItem(historyOptions, 'PrintPrevYPos', -1000, -1000, 10000,
                  _('Window Geometry'))

def setToolbarOptionDefaults(toolbarOptions):
    """Set defaults for toolbar geometry and buttons.
    """
    StringOptionItem = options.StringOptionItem
    IntOptionItem = options.IntOptionItem
    IntOptionItem(toolbarOptions, 'ToolbarQuantity', 2, 0, 20,
                  _('Toolbar Geometry'))
    IntOptionItem(toolbarOptions, 'ToolbarSize', 16, 1, 128,
                  _('Toolbar Geometry'))
    StringOptionItem(toolbarOptions, 'ToolbarPosition', '', True, False,
                     _('Toolbar Geometry'))
    StringOptionItem(toolbarOptions, 'Toolbar0',
                     'FileNew,FileOpen,FileSave,,FilePrintPreview,FilePrint,,'
                     'EditUndo,EditRedo,,EditCut,EditCopy,EditPaste,,'
                     'DataConfigType', True, False, _('Toolbar Commands'))
    StringOptionItem(toolbarOptions, 'Toolbar1',
                     'NodeInsertAfter,NodeAddChild,,NodeDelete,NodeIndent,'
                     'NodeUnindent,,NodeMoveUp,NodeMoveDown,,'
                     'ViewPrevSelect,ViewNextSelect,,ViewShowDescend',
                     True, False, _('Toolbar Commands'))

def setKeyboardOptionDefaults(keyboardOptions):
    """Set defaults for keyboard shortcuts.
    """
    KeyOptionItem = options.KeyOptionItem
    KeyOptionItem(keyboardOptions, 'FileNew', 'Ctrl+N', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileOpen', 'Ctrl+O', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileOpenSample', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileImport', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileSave', 'Ctrl+S', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileSaveAs', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileExport', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileProperties', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FilePrintSetup', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FilePrintPreview', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FilePrint', 'Ctrl+P', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FilePrintPdf', '', 'File Menu')
    KeyOptionItem(keyboardOptions, 'FileQuit', 'Ctrl+Q', 'File Menu')
    KeyOptionItem(keyboardOptions, 'EditUndo', 'Ctrl+Z', 'Edit Menu')
    KeyOptionItem(keyboardOptions, 'EditRedo', 'Ctrl+Y', 'Edit Menu')
    KeyOptionItem(keyboardOptions, 'EditCut', 'Ctrl+X', 'Edit Menu')
    KeyOptionItem(keyboardOptions, 'EditCopy', 'Ctrl+C', 'Edit Menu')
    KeyOptionItem(keyboardOptions, 'EditPaste', 'Ctrl+V', 'Edit Menu')
    KeyOptionItem(keyboardOptions, 'EditPastePlain', '', 'Edit Menu')
    KeyOptionItem(keyboardOptions, 'EditPasteClone', '', 'Edit Menu')
    KeyOptionItem(keyboardOptions, 'NodeRename', 'Ctrl+R', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeInsertBefore', 'Ctrl+B', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeInsertAfter', 'Ctrl+I', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeAddChild', 'Ctrl+A', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeDelete', 'Del', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeIndent', 'Ctrl+Shift+Right',
                  'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeUnindent', 'Ctrl+Shift+Left',
                  'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeMoveUp', 'Ctrl+Shift+Up', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeMoveDown', 'Ctrl+Shift+Down',
                  'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeMoveFirst', '', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'NodeMoveLast', '', 'Node Menu')
    KeyOptionItem(keyboardOptions, 'DataNodeType', 'Ctrl+T', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataConfigType', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataCopyType', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataSortNodes', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataNumbering', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataFlatCategory', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataAddCategory', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataFlatLink', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'DataArrangeLink', '', 'Data Menu')
    KeyOptionItem(keyboardOptions, 'ToolsFindText', 'Ctrl+F', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsFindCondition', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsFindReplace', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsFilterText', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsFilterCondition', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsSpellCheck', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsGenOptions', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsShortcuts', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsToolbars', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'ToolsFonts', '', 'Tools Menu')
    KeyOptionItem(keyboardOptions, 'FormatBoldFont', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatItalicFont', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatUnderlineFont', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatFontSize', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatFontColor', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatExtLink', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatIntLink', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatSelectAll', 'Ctrl+L', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'FormatClearFormat', '', 'Format Menu')
    KeyOptionItem(keyboardOptions, 'ViewExpandBranch', 'Ctrl+Right',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewCollapseBranch', 'Ctrl+Left',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewPrevSelect', 'Ctrl+Shift+P',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewNextSelect', 'Ctrl+Shift+N',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewDataOutput', 'Ctrl+Shift+O',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewDataEditor', 'Ctrl+Shift+E',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewTitleList', 'Ctrl+Shift+T',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewBreadcrumb', '', 'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewShowChildPane', 'Ctrl+Shift+C',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'ViewShowDescend', 'Ctrl+Shift+D',
                  'View Menu')
    KeyOptionItem(keyboardOptions, 'WinNewWindow', '', 'Window Menu')
    KeyOptionItem(keyboardOptions, 'WinCloseWindow', '', 'Window Menu')
    KeyOptionItem(keyboardOptions, 'HelpBasic', '', 'Help Menu')
    KeyOptionItem(keyboardOptions, 'HelpFull', '', 'Help Menu')
    KeyOptionItem(keyboardOptions, 'HelpAbout', '', 'Help Menu')
    KeyOptionItem(keyboardOptions, 'HelpPlugin', '', 'Help Menu')
    KeyOptionItem(keyboardOptions, 'IncremSearchStart', 'Ctrl+/', 'No Menu')
    KeyOptionItem(keyboardOptions, 'IncremSearchNext', 'F3', 'No Menu')
    KeyOptionItem(keyboardOptions, 'IncremSearchPrev', 'Shift+F3', 'No Menu')
