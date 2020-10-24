#!/usr/bin/env python3

#******************************************************************************
# configdialog.py, provides classes for the type configuration dialog
#
# TreeLine, an information storage program
# Copyright (C) 2020, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re
import copy
import operator
from PyQt5.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                             QCheckBox, QComboBox, QDialog, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QMenu,
                             QMessageBox, QPushButton, QScrollArea,
                             QSizePolicy, QSpinBox, QTabWidget, QTextEdit,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)
import nodeformat
import fieldformat
import icondict
import conditional
import matheval
import globalref


class ConfigDialog(QDialog):
    """Class override for the main config dialog
    
    Contains the tabbed pages that handle the actual settings.
    """
    dialogShown = pyqtSignal(bool)
    treeStruct = None
    formatsRef = None
    currentTypeName = ''
    currentFieldName = ''
    def __init__(self, parent=None):
        """Initialize the config dialog.

        Arguments:
            parent -- the parent window
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle(_('Configure Data Types'))
        self.prevPage = None
        self.localControl = None
        self.selectionModel = None

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)

        self.tabs = QTabWidget()
        topLayout.addWidget(self.tabs)
        typeListPage = TypeListPage(self)
        self.tabs.addTab(typeListPage, _('T&ype List'))
        typeConfigPage = TypeConfigPage(self)
        self.tabs.addTab(typeConfigPage, _('Typ&e Config'))
        fieldListPage = FieldListPage(self)
        self.tabs.addTab(fieldListPage, _('Field &List'))
        fieldConfigPage = FieldConfigPage(self)
        self.tabs.addTab(fieldConfigPage, _('&Field Config'))
        outputPage = OutputPage(self)
        self.tabs.addTab(outputPage, _('O&utput'))
        self.tabs.currentChanged.connect(self.updatePage)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        self.advancedButton = QPushButton(_('&Show Advanced'))
        ctrlLayout.addWidget(self.advancedButton)
        self.advancedButton.setCheckable(True)
        self.advancedButton.clicked.connect(self.toggleAdavanced)
        ctrlLayout.addStretch()
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.applyAndClose)
        self.applyButton = QPushButton(_('&Apply'))
        ctrlLayout.addWidget(self.applyButton)
        self.applyButton.clicked.connect(self.applyChanges)
        self.resetButton = QPushButton(_('&Reset'))
        ctrlLayout.addWidget(self.resetButton)
        self.resetButton.clicked.connect(self.reset)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.resetAndClose)

    def setRefs(self, localControl, resetSelect=False, forceCopy=False):
        """Set refs to model and formats, then update dialog data.

        Sets current type to current node's type if resetSelect or if invalid.
        Sets current field to first field if resetSelect or if invalid.
        Arguments:
            localControl -- a reference to the local control
            resetSelect -- if True, forces reset of current selections
            forceCopy -- if True, force making a new copy of formats
        """
        self.localControl = localControl
        ConfigDialog.treeStruct = localControl.structure
        ConfigDialog.formatsRef = (ConfigDialog.treeStruct.
                                   getConfigDialogFormats(forceCopy))
        self.selectionModel = localControl.currentSelectionModel()
        self.updateSelections(resetSelect)
        self.setModified(modified=False)
        self.prevPage = None
        self.updatePage()

    def updateSelections(self, forceUpdate=False):
        """Sets current type & current field if invalid or forceUpdate is True.

        Arguments:
            forceUpdate -- if True, forces reset of current selections
        """
        if forceUpdate or (ConfigDialog.currentTypeName not in
                           ConfigDialog.formatsRef):
            try:
                ConfigDialog.currentTypeName = (self.selectionModel.
                                                currentNode().formatRef.name)
            except AttributeError:   # no current node
                ConfigDialog.currentTypeName = (ConfigDialog.treeStruct.
                                                childList[0].formatRef.name)
        if forceUpdate or (ConfigDialog.currentFieldName not in
                           ConfigDialog.formatsRef[ConfigDialog.
                           currentTypeName].fieldNames()):
            ConfigDialog.currentFieldName = (ConfigDialog.
                                             formatsRef[ConfigDialog.
                                                        currentTypeName].
                                             fieldNames()[0])

    def updatePage(self):
        """Update new page and advanced button state when changing tabs.
        """
        if self.prevPage:
            self.prevPage.readChanges()
        page = self.tabs.currentWidget()
        self.advancedButton.setEnabled(len(page.advancedWidgets))
        page.toggleAdvanced(self.advancedButton.isChecked())
        page.updateContent()
        self.prevPage = page

    def setModified(self, dummyArg=None, modified=True):
        """Set the format to a modified status and update the controls.

        Arguments:
            dummyArg -- placeholder for unused signal arguments
            modified -- set to modified if True
        """
        ConfigDialog.formatsRef.configModified = modified
        self.applyButton.setEnabled(modified)
        self.resetButton.setEnabled(modified)

    def toggleAdavanced(self, show):
        """Toggle the display of advanced widgets in the sub-dialogs.

        Arguments:
            show -- show if true, hide if false
        """
        if show:
            self.advancedButton.setText(_('&Hide Advanced'))
        else:
            self.advancedButton.setText(_('&Show Advanced'))
        page = self.tabs.currentWidget()
        page.toggleAdvanced(show)

    def reset(self):
        """Set the formats back to original settings.
        """
        ConfigDialog.formatsRef = (ConfigDialog.treeStruct.
                                   getConfigDialogFormats(True))
        self.updateSelections()
        self.setModified(modified=False)
        self.prevPage = None
        self.updatePage()

    def applyChanges(self):
        """Apply copied format changes to the main format.

        Return False if there is a circular math reference.
        """
        self.tabs.currentWidget().readChanges()
        if ConfigDialog.formatsRef.configModified:
            try:
                ConfigDialog.treeStruct.applyConfigDialogFormats()
            except matheval.CircularMathError:
                QMessageBox.warning(self, 'TreeLine',
                       _('Error - circular reference in math field equations'))
                return False
            self.setModified(modified=False)
            self.localControl.updateAll()
        return True

    def applyAndClose(self):
        """Apply copied format changes to the main format and close the dialog.
        """
        if self.applyChanges():
            self.close()

    def resetAndClose(self):
        """Set the formats back to original settings and close the dialog.
        """
        self.reset()
        self.close()

    def closeEvent(self, event):
        """Signal that the dialog is closing.

        Arguments:
            event -- the close event
        """
        self.dialogShown.emit(False)


class ConfigPage(QWidget):
    """Abstract base class for config dialog tabbed pages.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.mainDialogRef = parent
        self.advancedWidgets = []

    def updateContent(self):
        """Update page contents from current format settings.

        Base class does nothing.
        """
        pass

    def readChanges(self):
        """Make changes to the format for each widget.

        Base class does nothing.
        """
        pass

    def changeCurrentType(self, typeName):
        """Change the current format type based on a signal from lists.

        Arguments:
            typeName -- the name of the new current type
        """
        self.readChanges()
        ConfigDialog.currentTypeName = typeName
        ConfigDialog.currentFieldName = (ConfigDialog.formatsRef[typeName].
                                         fieldNames()[0])
        if type(self) != TypeListPage:
            # "if" statement added to work around list view selection bug
            self.updateContent()

    def changeCurrentField(self, fieldName):
        """Change the current format field based on a signal from lists.

        Arguments:
            fieldName -- the name of the new current field
        """
        self.readChanges()
        ConfigDialog.currentFieldName = fieldName
        self.updateContent()

    def toggleAdvanced(self, show=True):
        """Toggle the display state of advanced widgets.
        
        Arguments:
            show -- show if true, hide if false
        """
        for widget in self.advancedWidgets:
            widget.setVisible(show)


class TypeListPage(ConfigPage):
    """Config dialog page with an editable list of node types.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        topLayout = QVBoxLayout(self)
        box = QGroupBox(_('Add or Remove Data Types'))
        topLayout.addWidget(box)
        horizLayout = QHBoxLayout(box)
        self.listBox = QListWidget()
        self.listBox.setSelectionMode(QAbstractItemView.SingleSelection)
        horizLayout.addWidget(self.listBox)
        self.listBox.currentTextChanged.connect(self.changeCurrentType)

        buttonLayout = QVBoxLayout()
        horizLayout.addLayout(buttonLayout)
        newButton = QPushButton(_('&New Type...'))
        buttonLayout.addWidget(newButton)
        newButton.clicked.connect(self.newType)
        copyButton = QPushButton(_('Co&py Type...'))
        buttonLayout.addWidget(copyButton)
        copyButton.clicked.connect(self.copyType)
        renameButton = QPushButton(_('Rena&me Type...'))
        buttonLayout.addWidget(renameButton)
        renameButton.clicked.connect(self.renameType)
        deleteButton = QPushButton(_('&Delete Type'))
        buttonLayout.addWidget(deleteButton)
        deleteButton.clicked.connect(self.deleteType)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        names = ConfigDialog.formatsRef.typeNames()
        self.listBox.blockSignals(True)
        self.listBox.clear()
        self.listBox.addItems(names)
        self.listBox.setCurrentRow(names.index(ConfigDialog.currentTypeName))
        self.listBox.blockSignals(False)

    def newType(self):
        """Create a new type based on button signal.
        """
        dlg = NameEntryDialog(_('Add Type'), _('Enter new type name:'), '', '',
                              ConfigDialog.formatsRef.typeNames(), self)
        if dlg.exec_() == QDialog.Accepted:
            newFormat = nodeformat.NodeFormat(dlg.text,
                                              ConfigDialog.formatsRef, None,
                                              True)
            ConfigDialog.formatsRef[dlg.text] = newFormat
            ConfigDialog.currentTypeName = dlg.text
            ConfigDialog.currentFieldName = newFormat.fieldNames()[0]
            self.updateContent()
            self.mainDialogRef.setModified()

    def copyType(self):
        """Copy selected type based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = NameEntryDialog(_('Copy Type'), _('Enter new type name:'),
                              ConfigDialog.currentTypeName,
                              _('&Derive from original'),
                              ConfigDialog.formatsRef.typeNames(), self)
        if currentFormat.genericType:
            dlg.extraCheckBox.setEnabled(False)
        if dlg.exec_() == QDialog.Accepted:
            newFormat = copy.deepcopy(currentFormat)
            newFormat.name = dlg.text
            # avoid using copied reference for parentFormats
            newFormat.parentFormats = currentFormat.parentFormats
            ConfigDialog.formatsRef[dlg.text] = newFormat
            ConfigDialog.currentTypeName = dlg.text
            if dlg.extraChecked:
                newFormat.genericType = currentFormat.name
            ConfigDialog.formatsRef.updateDerivedRefs()
            self.updateContent()
            self.mainDialogRef.setModified()

    def renameType(self):
        """Rename the selected type based on button signal.
        """
        oldName = ConfigDialog.currentTypeName
        dlg = NameEntryDialog(_('Rename Type'),
                              _('Rename from {} to:').format(oldName), oldName,
                              '', ConfigDialog.formatsRef.typeNames(), self)
        if dlg.exec_() == QDialog.Accepted:
            currentType = ConfigDialog.formatsRef[oldName]
            currentType.name = dlg.text
            del ConfigDialog.formatsRef[oldName]
            ConfigDialog.formatsRef[dlg.text] = currentType
            # reverse the rename dict - find original name (multiple renames)
            reverseDict = {}
            for old, new in ConfigDialog.formatsRef.typeRenameDict.items():
                reverseDict[new] = old
            origName = reverseDict.get(oldName, oldName)
            ConfigDialog.formatsRef.typeRenameDict[origName] = dlg.text
            if oldName in ConfigDialog.formatsRef.fieldRenameDict:
                ConfigDialog.formatsRef.fieldRenameDict[dlg.text] = \
                        ConfigDialog.formatsRef.fieldRenameDict[oldName]
                del ConfigDialog.formatsRef.fieldRenameDict[oldName]
            for nodeType in ConfigDialog.formatsRef.values():
                if nodeType.childType == oldName:
                    nodeType.childType = dlg.text
                if nodeType.genericType == oldName:
                    nodeType.genericType = dlg.text
                if oldName in nodeType.childTypeLimit:
                    nodeType.childTypeLimit.remove(oldName)
                    nodeType.childTypeLimit.add(dlg.text)
            ConfigDialog.currentTypeName = dlg.text
            self.updateContent()
            self.mainDialogRef.setModified()

    def deleteType(self):
        """Delete the selected type based on button signal.
        """
        # reverse the rename dict - find original name (before any rename)
        reverseDict = {}
        for old, new in ConfigDialog.formatsRef.typeRenameDict.items():
            reverseDict[new] = old
        origName = reverseDict.get(ConfigDialog.currentTypeName,
                                   ConfigDialog.currentTypeName)
        if ConfigDialog.treeStruct.usesType(origName):
            QMessageBox.warning(self, 'TreeLine',
                              _('Cannot delete data type being used by nodes'))
            return
        del ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        if origName != ConfigDialog.currentTypeName:
            del ConfigDialog.formatsRef.typeRenameDict[origName]
        for nodeType in ConfigDialog.formatsRef.values():
            if nodeType.childType == ConfigDialog.currentTypeName:
                nodeType.childType = ''
            if nodeType.genericType == ConfigDialog.currentTypeName:
                nodeType.genericType = ''
                nodeType.conditional = None
            nodeType.childTypeLimit.discard(ConfigDialog.currentTypeName)
        ConfigDialog.formatsRef.updateDerivedRefs()
        ConfigDialog.currentTypeName = ConfigDialog.formatsRef.typeNames()[0]
        ConfigDialog.currentFieldName = ConfigDialog.formatsRef[ConfigDialog.
                                               currentTypeName].fieldNames()[0]
        self.updateContent()
        self.mainDialogRef.setModified()


_noTypeSetName = _('[None]', 'no type set')

class TypeConfigPage(ConfigPage):
    """Config dialog page to change parmaters of a node type.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        topLayout = QGridLayout(self)
        typeBox = QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox, 0, 0)
        typeLayout = QVBoxLayout(typeBox)
        self.typeCombo = QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        childBox = QGroupBox(_('Default Child &Type'))
        topLayout.addWidget(childBox, 0, 1)
        childLayout = QVBoxLayout(childBox)
        self.childCombo = QComboBox()
        childLayout.addWidget(self.childCombo)
        self.childCombo.currentIndexChanged.connect(self.mainDialogRef.
                                                    setModified)

        iconBox = QGroupBox(_('Icon'))
        topLayout.addWidget(iconBox, 1, 1)
        iconLayout = QHBoxLayout(iconBox)
        self.iconImage = QLabel()
        iconLayout.addWidget(self.iconImage)
        self.iconImage.setAlignment(Qt.AlignCenter)
        iconButton = QPushButton(_('Change &Icon'))
        iconLayout.addWidget(iconButton)
        iconButton.clicked.connect(self.changeIcon)

        optionsBox = QGroupBox(_('Output Options'))
        topLayout.addWidget(optionsBox, 1, 0, 2, 1)
        optionsLayout =  QVBoxLayout(optionsBox)
        self.blanksButton = QCheckBox(_('Add &blank lines between '
                                              'nodes'))
        optionsLayout.addWidget(self.blanksButton)
        self.blanksButton.toggled.connect(self.mainDialogRef.setModified)
        self.htmlButton = QCheckBox(_('Allow &HTML rich text in format'))
        optionsLayout.addWidget(self.htmlButton)
        self.htmlButton.toggled.connect(self.mainDialogRef.setModified)
        self.bulletButton = QCheckBox(_('Add text bullet&s'))
        optionsLayout.addWidget(self.bulletButton)
        self.bulletButton.toggled.connect(self.changeUseBullets)
        self.tableButton = QCheckBox(_('Use a table for field &data'))
        optionsLayout.addWidget(self.tableButton)
        self.tableButton.toggled.connect(self.changeUseTable)

        # advanced widgets
        outputSepBox = QGroupBox(_('Combination && Child List Output '
                                   '&Separator'))
        topLayout.addWidget(outputSepBox, 2, 1)
        self.advancedWidgets.append(outputSepBox)
        outputSepLayout = QVBoxLayout(outputSepBox)
        self.outputSepEdit = QLineEdit()
        outputSepLayout.addWidget(self.outputSepEdit)
        sizePolicy = self.outputSepEdit.sizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Preferred)
        self.outputSepEdit.setSizePolicy(sizePolicy)
        self.outputSepEdit.textEdited.connect(self.mainDialogRef.setModified)

        genericBox = QGroupBox(_('Derived from &Generic Type'))
        topLayout.addWidget(genericBox, 3, 0)
        self.advancedWidgets.append(genericBox)
        genericLayout = QVBoxLayout(genericBox)
        self.genericCombo = QComboBox()
        genericLayout.addWidget(self.genericCombo)
        self.genericCombo.currentIndexChanged.connect(self.setConditionAvail)
        self.genericCombo.currentIndexChanged.connect(self.mainDialogRef.
                                                      setModified)

        conditionBox = QGroupBox(_('Automatic Types'))
        topLayout.addWidget(conditionBox, 3, 1)
        self.advancedWidgets.append(conditionBox)
        conditionLayout = QVBoxLayout(conditionBox)
        self.conditionButton = QPushButton()
        conditionLayout.addWidget(self.conditionButton)
        self.conditionButton.clicked.connect(self.showConditionDialog)

        typeLimitBox = QGroupBox(_('Child Type Limits'))
        topLayout.addWidget(typeLimitBox, 4, 0)
        self.advancedWidgets.append(typeLimitBox)
        typeLimitLayout = QVBoxLayout(typeLimitBox)
        self.typeLimitCombo = TypeLimitCombo()
        typeLimitLayout.addWidget(self.typeLimitCombo)
        self.typeLimitCombo.limitChanged.connect(self.mainDialogRef.
                                                 setModified)

        topLayout.setRowStretch(5, 1)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                       currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        self.childCombo.blockSignals(True)
        self.childCombo.clear()
        self.childCombo.addItem(_noTypeSetName)
        self.childCombo.addItems(typeNames)
        try:
            childItem = typeNames.index(currentFormat.childType) + 1
        except ValueError:
            childItem = 0
        self.childCombo.setCurrentIndex(childItem)
        self.childCombo.blockSignals(False)

        icon = globalref.treeIcons.getIcon(currentFormat.iconName, True)
        if icon:
            self.iconImage.setPixmap(icon.pixmap(16, 16))
        else:
            self.iconImage.setText(_('None'))

        self.blanksButton.blockSignals(True)
        self.blanksButton.setChecked(currentFormat.spaceBetween)
        self.blanksButton.blockSignals(False)

        self.htmlButton.blockSignals(True)
        self.htmlButton.setChecked(currentFormat.formatHtml)
        self.htmlButton.blockSignals(False)

        self.bulletButton.blockSignals(True)
        self.bulletButton.setChecked(currentFormat.useBullets)
        self.bulletButton.blockSignals(False)

        self.tableButton.blockSignals(True)
        self.tableButton.setChecked(currentFormat.useTables)
        self.tableButton.blockSignals(False)

        self.htmlButton.setEnabled(not currentFormat.useBullets and
                                   not currentFormat.useTables)

        self.outputSepEdit.setText(currentFormat.outputSeparator)

        self.genericCombo.blockSignals(True)
        self.genericCombo.clear()
        self.genericCombo.addItem(_noTypeSetName)
        genTypeNames = [name for name in typeNames if
                        name != ConfigDialog.currentTypeName and
                        not ConfigDialog.formatsRef[name].genericType]
        self.genericCombo.addItems(genTypeNames)
        try:
            generic = genTypeNames.index(currentFormat.genericType) + 1
        except ValueError:
            generic = 0
        self.genericCombo.setCurrentIndex(generic)
        self.genericCombo.blockSignals(False)
        self.setConditionAvail()

        self.typeLimitCombo.updateLists(typeNames,
                                        currentFormat.childTypeLimit)

    def changeIcon(self):
        """Show the change icon dialog based on a button press.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = IconSelectDialog(currentFormat, self)
        if (dlg.exec_() == QDialog.Accepted and
            dlg.currentIconName != currentFormat.iconName):
            currentFormat.iconName = dlg.currentIconName
            self.mainDialogRef.setModified()
            self.updateContent()

    def changeUseBullets(self, checked=True):
        """Change setting to use bullets for output.

        Does not allow bullets and table to both be checked, and
        automatically checks use HTML.
        Arguments:
            checked -- True if bullets are selected
        """
        if checked:
            self.tableButton.setChecked(False)
            self.htmlButton.setChecked(True)
        self.htmlButton.setEnabled(not checked)
        self.mainDialogRef.setModified()

    def changeUseTable(self, checked=True):
        """Change setting to use tables for output.

        Does not allow bullets and table to both be checked, and
        automatically checks use HTML.
        Arguments:
            checked -- True if tables are selected
        """
        if checked:
            self.bulletButton.setChecked(False)
            self.htmlButton.setChecked(True)
        self.htmlButton.setEnabled(not checked)
        self.mainDialogRef.setModified()

    def setConditionAvail(self):
        """Enable conditional button if generic or dervived type.

        Set button text based on presence of conditions.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        if self.genericCombo.currentIndex() > 0 or currentFormat.derivedTypes:
            self.conditionButton.setEnabled(True)
            if currentFormat.conditional:
                self.conditionButton.setText(_('Modify Co&nditional Types'))
                return
        else:
            self.conditionButton.setEnabled(False)
        self.conditionButton.setText(_('Create Co&nditional Types'))

    def showConditionDialog(self):
        """Show the dialog to create or modify conditional types.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dialog = conditional.ConditionDialog(conditional.FindDialogType.
                                             typeDialog,
                                             _('Set Types Conditionally'),
                                             currentFormat)
        if currentFormat.conditional:
            dialog.setCondition(currentFormat.conditional)
        if dialog.exec_() == QDialog.Accepted:
            currentFormat.conditional = dialog.conditional()
            if not currentFormat.conditional:
                currentFormat.conditional = None
            ConfigDialog.formatsRef.updateDerivedRefs()
            self.mainDialogRef.setModified()
            self.updateContent()

    def readChanges(self):
        """Make changes to the format for each widget.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        currentFormat.childType = self.childCombo.currentText()
        if currentFormat.childType == _noTypeSetName:
            currentFormat.childType = ''
        currentFormat.outputSeparator = self.outputSepEdit.text()
        prevGenericType = currentFormat.genericType
        currentFormat.genericType = self.genericCombo.currentText()
        if currentFormat.genericType == _noTypeSetName:
            currentFormat.genericType = ''
        if currentFormat.genericType != prevGenericType:
            ConfigDialog.formatsRef.updateDerivedRefs()
            currentFormat.updateFromGeneric(formatsRef=ConfigDialog.formatsRef)
            if ConfigDialog.currentFieldName not in currentFormat.fieldNames():
                ConfigDialog.currentFieldName = currentFormat.fieldNames()[0]
        currentFormat.spaceBetween = self.blanksButton.isChecked()
        currentFormat.formatHtml = self.htmlButton.isChecked()
        currentFormat.childTypeLimit = self.typeLimitCombo.selectSet
        useBullets = self.bulletButton.isChecked()
        useTables = self.tableButton.isChecked()
        if (useBullets != currentFormat.useBullets or
            useTables != currentFormat.useTables):
            currentFormat.useBullets = useBullets
            currentFormat.useTables = useTables
            if useBullets:
                currentFormat.addBullets()
            elif useTables:
                currentFormat.addTables()
            else:
                currentFormat.clearBulletsAndTables()


class FieldListPage(ConfigPage):
    """Config dialog page with an editable list of fields.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        topLayout = QVBoxLayout(self)
        typeBox = QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox)
        typeLayout = QVBoxLayout(typeBox)
        self.typeCombo = QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        fieldBox = QGroupBox(_('Modify &Field List'))
        topLayout.addWidget(fieldBox)
        horizLayout = QHBoxLayout(fieldBox)
        self.fieldListBox = QTreeWidget()
        horizLayout.addWidget(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setColumnCount(3)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type'),
                                           _('Sort Key')])
        self.fieldListBox.currentItemChanged.connect(self.changeField)

        buttonLayout = QVBoxLayout()
        horizLayout.addLayout(buttonLayout)
        self.upButton = QPushButton(_('Move U&p'))
        buttonLayout.addWidget(self.upButton)
        self.upButton.clicked.connect(self.moveUp)
        self.downButton = QPushButton(_('Move Do&wn'))
        buttonLayout.addWidget(self.downButton)
        self.downButton.clicked.connect(self.moveDown)
        self.newButton = QPushButton(_('&New Field...'))
        buttonLayout.addWidget(self.newButton)
        self.newButton.clicked.connect(self.newField)
        self.renameButton = QPushButton(_('Rena&me Field...'))
        buttonLayout.addWidget(self.renameButton)
        self.renameButton.clicked.connect(self.renameField)
        self.deleteButton = QPushButton(_('Dele&te Field'))
        buttonLayout.addWidget(self.deleteButton)
        self.deleteButton.clicked.connect(self.deleteField)
        sortKeyButton = QPushButton(_('Sort &Keys...'))
        buttonLayout.addWidget(sortKeyButton)
        sortKeyButton.clicked.connect(self.defineSortKeys)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                       currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        sortFields = [field for field in currentFormat.fields() if
                      field.sortKeyNum > 0]
        sortFields.sort(key = operator.attrgetter('sortKeyNum'))
        if not sortFields:
            sortFields = [list(currentFormat.fields())[0]]
        self.fieldListBox.blockSignals(True)
        self.fieldListBox.clear()
        for field in currentFormat.fields():
            try:
                sortKey = repr(sortFields.index(field) + 1)
                sortDir = _('fwd') if field.sortKeyForward else _('rev')
                sortKey = '{0} ({1})'.format(sortKey, sortDir)
            except ValueError:
                sortKey = ''
            typeName = fieldformat.translatedTypeName(field.typeName)
            QTreeWidgetItem(self.fieldListBox, [field.name, typeName, sortKey])
        selectNum = currentFormat.fieldNames().index(ConfigDialog.
                                                     currentFieldName)
        selectItem = self.fieldListBox.topLevelItem(selectNum)
        self.fieldListBox.setCurrentItem(selectItem)
        selectItem.setSelected(True)
        width = self.fieldListBox.viewport().width()
        self.fieldListBox.setColumnWidth(0, int(width // 2.5))
        self.fieldListBox.setColumnWidth(1, int(width // 2.5))
        self.fieldListBox.setColumnWidth(2, width // 5)
        self.fieldListBox.blockSignals(False)
        num = currentFormat.fieldNames().index(ConfigDialog.currentFieldName)
        self.upButton.setEnabled(num > 0 and not  currentFormat.genericType)
        self.downButton.setEnabled(num < len(currentFormat.fieldDict) - 1 and
                                   not currentFormat.genericType)
        self.newButton.setEnabled(not currentFormat.genericType)
        self.renameButton.setEnabled(not currentFormat.genericType)
        self.deleteButton.setEnabled(len(currentFormat.fieldDict) > 1 and
                                     not currentFormat.genericType)

    def changeField(self, currentItem, prevItem):
        """Change the current format field based on a tree widget signal.

        Arguments:
            currentItem -- the new current tree widget item
            prevItem -- the old current tree widget item
        """
        self.changeCurrentField(currentItem.text(0))

    def moveUp(self):
        """Move field upward in the list based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        fieldList = currentFormat.fieldNames()
        num = fieldList.index(ConfigDialog.currentFieldName)
        if num > 0:
            fieldList[num-1], fieldList[num] = fieldList[num], fieldList[num-1]
            currentFormat.reorderFields(fieldList)
            currentFormat.updateDerivedTypes()
            self.updateContent()
            self.mainDialogRef.setModified()

    def moveDown(self):
        """Move field downward in the list based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        fieldList = currentFormat.fieldNames()
        num = fieldList.index(ConfigDialog.currentFieldName)
        if num < len(fieldList) - 1:
            fieldList[num], fieldList[num+1] = fieldList[num+1], fieldList[num]
            currentFormat.reorderFields(fieldList)
            currentFormat.updateDerivedTypes()
            self.updateContent()
            self.mainDialogRef.setModified()

    def newField(self):
        """Create and add a new field based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = NameEntryDialog(_('Add Field'), _('Enter new field name:'), '',
                              '', currentFormat.fieldNames(), self)
        if dlg.exec_() == QDialog.Accepted:
            currentFormat.addField(dlg.text)
            ConfigDialog.currentFieldName = dlg.text
            currentFormat.updateDerivedTypes()
            self.updateContent()
            self.mainDialogRef.setModified()

    def renameField(self):
        """Prompt for new name and rename field based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        fieldList = currentFormat.fieldNames()
        oldName = ConfigDialog.currentFieldName
        dlg = NameEntryDialog(_('Rename Field'),
                              _('Rename from {} to:').format(oldName), oldName,
                              '', fieldList, self)
        if dlg.exec_() == QDialog.Accepted:
            num = fieldList.index(oldName)
            fieldList[num] = dlg.text
            for nodeFormat in [currentFormat] + currentFormat.derivedTypes:
                field = nodeFormat.fieldDict[oldName]
                field.name = dlg.text
                nodeFormat.fieldDict[field.name] = field
                nodeFormat.reorderFields(fieldList)
                if nodeFormat.conditional:
                    nodeFormat.conditional.renameFields(oldName, field.name)
                # savedConditions = {}
                # for name, text in nodeFormat.savedConditionText.items():
                    # condition = conditional.Conditional(text, nodeFormat.name)
                    # condition.renameFields(oldName, field.name)
                    # savedConditions[name] = condition.conditionStr()
                # nodeFormat.savedConditionText = savedConditions
                renameDict = (ConfigDialog.formatsRef.fieldRenameDict.
                              setdefault(nodeFormat.name, {}))
                # reverse rename dict - find original name (multiple renames)
                reverseDict = {}
                for old, new in renameDict.items():
                    reverseDict[new] = old
                origName = reverseDict.get(oldName, oldName)
                renameDict[origName] = dlg.text
            ConfigDialog.currentFieldName = dlg.text
            self.updateContent()
            self.mainDialogRef.setModified()

    def deleteField(self):
        """Delete field based on button signal.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        num = currentFormat.fieldNames().index(ConfigDialog.currentFieldName)
        for nodeFormat in [currentFormat] + currentFormat.derivedTypes:
            field = nodeFormat.fieldDict[ConfigDialog.currentFieldName]
            nodeFormat.removeField(field)
            del nodeFormat.fieldDict[ConfigDialog.currentFieldName]
        if num > 0:
            num -= 1
        ConfigDialog.currentFieldName = currentFormat.fieldNames()[num]
        ConfigDialog.formatsRef.updateDerivedRefs()
        self.updateContent()
        self.mainDialogRef.setModified()

    def defineSortKeys(self):
        """Show a dialog to change sort key fields and directions.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        dlg = SortKeyDialog(currentFormat.fieldDict, self)
        if dlg.exec_() == QDialog.Accepted:
            self.updateContent()
            self.mainDialogRef.setModified()


_fileInfoFormatName = _('File Info Reference')

class FieldConfigPage(ConfigPage):
    """Config dialog page to change parmaters of a field.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.currentFileInfoField = ''

        topLayout = QGridLayout(self)
        typeBox = QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox, 0, 0)
        typeLayout = QVBoxLayout(typeBox)
        self.typeCombo = QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        fieldBox = QGroupBox(_('F&ield'))
        topLayout.addWidget(fieldBox, 0, 1)
        fieldLayout = QVBoxLayout(fieldBox)
        self.fieldCombo = QComboBox()
        fieldLayout.addWidget(self.fieldCombo)
        self.fieldCombo.currentIndexChanged[str].connect(self.
                                                         changeCurrentField)

        fieldTypeBox = QGroupBox(_('&Field Type'))
        topLayout.addWidget(fieldTypeBox, 1, 0)
        fieldTypeLayout = QVBoxLayout(fieldTypeBox)
        self.fieldTypeCombo = QComboBox()
        fieldTypeLayout.addWidget(self.fieldTypeCombo)
        self.fieldTypeCombo.addItems(fieldformat.translatedFieldTypes)
        self.fieldTypeCombo.currentIndexChanged.connect(self.changeFieldType)

        self.formatBox = QGroupBox(_('Outpu&t Format'))
        topLayout.addWidget(self.formatBox, 1, 1)
        formatLayout = QHBoxLayout(self.formatBox)
        self.formatEdit = QLineEdit()
        formatLayout.addWidget(self.formatEdit)
        self.formatEdit.textEdited.connect(self.mainDialogRef.setModified)
        self.helpButton = QPushButton(_('Format &Help'))
        formatLayout.addWidget(self.helpButton)
        self.helpButton.clicked.connect(self.formatHelp)

        extraBox = QGroupBox(_('Extra Text'))
        topLayout.addWidget(extraBox, 2, 0, 2, 1)
        extraLayout = QVBoxLayout(extraBox)
        extraLayout.setSpacing(0)
        prefixLabel = QLabel(_('&Prefix'))
        extraLayout.addWidget(prefixLabel)
        self.prefixEdit = QLineEdit()
        extraLayout.addWidget(self.prefixEdit)
        prefixLabel.setBuddy(self.prefixEdit)
        self.prefixEdit.textEdited.connect(self.mainDialogRef.setModified)
        extraLayout.addSpacing(8)
        suffixLabel = QLabel(_('Suffi&x'))
        extraLayout.addWidget(suffixLabel)
        self.suffixEdit = QLineEdit()
        extraLayout.addWidget(self.suffixEdit)
        suffixLabel.setBuddy(self.suffixEdit)
        self.suffixEdit.textEdited.connect(self.mainDialogRef.setModified)

        defaultBox = QGroupBox(_('Default &Value for New Nodes'))
        topLayout.addWidget(defaultBox, 2, 1)
        defaultLayout = QVBoxLayout(defaultBox)
        self.defaultCombo = QComboBox()
        defaultLayout.addWidget(self.defaultCombo)
        self.defaultCombo.setEditable(True)
        self.defaultCombo.editTextChanged.connect(self.mainDialogRef.
                                                  setModified)

        self.heightBox = QGroupBox(_('Editor Height'))
        topLayout.addWidget(self.heightBox, 3, 1)
        heightLayout = QHBoxLayout(self.heightBox)
        heightLabel = QLabel(_('Num&ber of text lines'))
        heightLayout.addWidget(heightLabel)
        self.heightCtrl = QSpinBox()
        heightLayout.addWidget(self.heightCtrl)
        self.heightCtrl.setMinimum(1)
        self.heightCtrl.setMaximum(999)
        heightLabel.setBuddy(self.heightCtrl)
        self.heightCtrl.valueChanged.connect(self.mainDialogRef.setModified)

        self.equationBox = QGroupBox(_('Math Equation'))
        topLayout.addWidget(self.equationBox, 4, 0, 1, 2)
        equationLayout = QHBoxLayout(self.equationBox)
        self.equationViewer = QLineEdit()
        equationLayout.addWidget(self.equationViewer)
        self.equationViewer.setReadOnly(True)
        equationButton = QPushButton(_('Define Equation'))
        equationLayout.addWidget(equationButton)
        equationButton.clicked.connect(self.defineMathEquation)

        htmlBox = QGroupBox(_('Output HTML'))
        topLayout.addWidget(htmlBox, 5, 0)
        htmlLayout = QVBoxLayout(htmlBox)
        self.htmlButton = QCheckBox(_('Evaluate &HTML tags'))
        htmlLayout.addWidget(self.htmlButton)
        self.htmlButton.toggled.connect(self.mainDialogRef.setModified)

        topLayout.setRowStretch(6, 1)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.addItem(_fileInfoFormatName)
        if self.currentFileInfoField:
            self.typeCombo.setCurrentIndex(len(typeNames))
        else:
            self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                           currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat, currentField = self.currentFormatAndField()
        self.fieldCombo.blockSignals(True)
        self.fieldCombo.clear()
        self.fieldCombo.addItems(currentFormat.fieldNames())
        selectNum = currentFormat.fieldNames().index(currentField.name)
        self.fieldCombo.setCurrentIndex(selectNum)
        self.fieldCombo.blockSignals(False)

        self.fieldTypeCombo.blockSignals(True)
        selectNum = fieldformat.fieldTypes.index(currentField.typeName)
        self.fieldTypeCombo.setCurrentIndex(selectNum)
        self.fieldTypeCombo.blockSignals(False)
        # also disable for generic types
        self.fieldTypeCombo.setEnabled(not self.currentFileInfoField)

        self.formatBox.setEnabled(currentField.defaultFormat != '')
        if (hasattr(currentField, 'resultType') and
            currentField.resultType == fieldformat.MathResult.text):
            self.formatBox.setEnabled(False)
        self.formatEdit.setText(currentField.format)

        self.prefixEdit.setText(currentField.prefix)
        self.suffixEdit.setText(currentField.suffix)

        self.defaultCombo.blockSignals(True)
        self.defaultCombo.clear()
        initDefault = currentField.getEditorInitDefault()
        self.defaultCombo.addItem(initDefault)
        initDefaultList = currentField.initDefaultChoices()
        if initDefaultList:
            if initDefaultList[0] == initDefault:
                initDefaultList[0] = ''   # don't duplicate first entry
            self.defaultCombo.addItems(initDefaultList)
        self.defaultCombo.setCurrentIndex(0)
        self.defaultCombo.blockSignals(False)
        self.defaultCombo.setEnabled(currentField.supportsInitDefault and
                                     not self.currentFileInfoField)

        self.heightCtrl.blockSignals(True)
        self.heightCtrl.setValue(currentField.numLines)
        self.heightCtrl.blockSignals(False)
        self.heightBox.setEnabled(not self.currentFileInfoField and
                                  currentField.editorClassName in
                                  ('RichTextEditor', 'HtmlTextEditor',
                                   'PlainTextEditor'))
        self.htmlButton.blockSignals(True)
        self.htmlButton.setChecked(currentField.evalHtml)
        self.htmlButton.blockSignals(False)
        self.htmlButton.setEnabled(not currentField.fixEvalHtmlSetting)

        if currentField.typeName == 'Math':
            self.equationBox.show()
            eqnText = currentField.equationText()
            self.equationViewer.setText(eqnText)
        else:
            self.equationBox.hide()

    def currentFormatAndField(self):
        """Return a tuple of the current format and field.

        Adjusts for a current file info field.
        """
        if self.currentFileInfoField:
            currentFormat = ConfigDialog.formatsRef.fileInfoFormat
            fieldName = self.currentFileInfoField
        else:
            currentFormat = ConfigDialog.formatsRef[ConfigDialog.
                                                    currentTypeName]
            fieldName = ConfigDialog.currentFieldName
        currentField = currentFormat.fieldDict[fieldName]
        return (currentFormat, currentField)

    def changeCurrentType(self, typeName):
        """Change the current format type based on a signal from lists.

        Arguments:
            typeName -- the name of the new current type
        """
        self.readChanges()
        if typeName == _fileInfoFormatName:
            self.currentFileInfoField = (ConfigDialog.formatsRef.
                                         fileInfoFormat.fieldNames()[0])
        else:
            ConfigDialog.currentTypeName = typeName
            ConfigDialog.currentFieldName = (ConfigDialog.formatsRef[typeName].
                                             fieldNames()[0])
            self.currentFileInfoField = ''
        self.updateContent()

    def changeCurrentField(self, fieldName):
        """Change the current format field based on a signal from lists.

        Arguments:
            fieldName -- the name of the new current field
        """
        self.readChanges()
        if self.currentFileInfoField:
            self.currentFileInfoField = fieldName
        else:
            ConfigDialog.currentFieldName = fieldName
        self.updateContent()

    def changeFieldType(self):
        """Change the field type based on a combo box signal.
        """
        self.readChanges()   # preserve previous changes
        currentFormat, currentField = self.currentFormatAndField()
        selectNum = self.fieldTypeCombo.currentIndex()
        fieldTypeName = fieldformat.fieldTypes[selectNum]
        currentField.changeType(fieldTypeName)
        currentFormat.updateDerivedTypes()
        self.updateContent()
        self.mainDialogRef.setModified()

    def defineMathEquation(self):
        """Show the dialog to define an equation for a Math field.
        """
        currentFormat, currentField = self.currentFormatAndField()
        prevEqnText = currentField.equationText()
        prevResultType = currentField.resultType
        dlg = MathEquationDialog(currentFormat, currentField, self)
        if (dlg.exec_() == QDialog.Accepted and
            (currentField.equationText() != prevEqnText or
             currentField.resultType != prevResultType)):
            self.mainDialogRef.setModified()
            self.updateContent()

    def formatHelp(self):
        """Provide a format help menu based on a button signal.
        """
        currentFormat, currentField = self.currentFormatAndField()
        menu = QMenu(self)
        self.formatHelpDict = {}
        for descript, key in currentField.getFormatHelpMenuList():
            if descript:
                self.formatHelpDict[descript] = key
                menu.addAction(descript)
            else:
                menu.addSeparator()
        menu.popup(self.helpButton.
                   mapToGlobal(QPoint(0, self.helpButton.height())))
        menu.triggered.connect(self.insertFormat)

    def insertFormat(self, action):
        """Insert format text from help menu into edit box.

        Arguments:
            action -- the action from the help menu
        """
        self.formatEdit.insert(self.formatHelpDict[action.text()])

    def readChanges(self):
        """Make changes to the format for each widget.
        """
        currentFormat, currentField = self.currentFormatAndField()
        if not currentField.fixEvalHtmlSetting:
            currentField.evalHtml = self.htmlButton.isChecked()
        prevFormat = currentField.format
        try:
            currentField.setFormat(self.formatEdit.text())
            if (self.currentFileInfoField and
                self.formatEdit.text() != prevFormat):
                currentFormat.fieldFormatModified = True
        except ValueError:
            self.formatEdit.setText(currentField.format)
        currentField.prefix = self.prefixEdit.text()
        currentField.suffix = self.suffixEdit.text()
        if self.currentFileInfoField and (currentField.prefix or
                                          currentField.suffix):
            currentFormat.fieldFormatModified = True
        try:
            currentField.setInitDefault(self.defaultCombo.currentText())
        except ValueError:
            self.defaultCombo.blockSignals(True)
            self.defaultCombo.setEditText(currentField.getEditorInitDefault())
            self.defaultCombo.blockSignals(False)
        currentField.numLines = self.heightCtrl.value()


_refLevelList = ['No Other Reference', 'File Info Reference',
                 'Any Ancestor Reference', 'Parent Reference',
                 'Grandparent Reference', 'Great Grandparent Reference',
                 'Child Reference', 'Child Count']
# _refLevelFlags  correspond to _refLevelList
_refLevelFlags = ['', '!', '?', '*', '**', '***', '&', '#']
fieldPattern = re.compile(r'{\*.*?\*}')

class  OutputPage(ConfigPage):
    """Config dialog page to define the node output strings.
    """
    def __init__(self,  parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.refLevelFlag = ''
        self.refLevelType = None

        topLayout = QGridLayout(self)
        typeBox = QGroupBox(_('&Data Type'))
        topLayout.addWidget(typeBox, 0, 0)
        typeLayout = QVBoxLayout(typeBox)
        self.typeCombo = QComboBox()
        typeLayout.addWidget(self.typeCombo)
        self.typeCombo.currentIndexChanged[str].connect(self.changeCurrentType)

        fieldBox = QGroupBox(_('F&ield List'))
        topLayout.addWidget(fieldBox, 1, 0, 2, 1)
        boxLayout = QVBoxLayout(fieldBox)
        self.fieldListBox = QTreeWidget()
        boxLayout.addWidget(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.fieldListBox.setColumnCount(2)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type')])
        self.fieldListBox.itemSelectionChanged.connect(self.changeField)

        titleButtonLayout = QVBoxLayout()
        topLayout.addLayout(titleButtonLayout, 1, 1)
        self.toTitleButton = QPushButton('>>')
        titleButtonLayout.addWidget(self.toTitleButton)
        self.toTitleButton.setMaximumWidth(self.toTitleButton.
                                           sizeHint().height())
        self.toTitleButton.clicked.connect(self.fieldToTitle)
        self.delTitleButton = QPushButton('<<')
        titleButtonLayout.addWidget(self.delTitleButton)
        self.delTitleButton.setMaximumWidth(self.delTitleButton.
                                            sizeHint().height())
        self.delTitleButton.clicked.connect(self.delTitleField)

        titleBox = QGroupBox(_('&Title Format'))
        topLayout.addWidget(titleBox, 1, 2)
        titleLayout = QVBoxLayout(titleBox)
        self.titleEdit = TitleEdit()
        titleLayout.addWidget(self.titleEdit)
        self.titleEdit.cursorPositionChanged.connect(self.
                                                     setControlAvailability)
        self.titleEdit.textEdited.connect(self.mainDialogRef.setModified)

        outputButtonLayout = QVBoxLayout()
        topLayout.addLayout(outputButtonLayout, 2, 1)
        self.toOutputButton = QPushButton('>>')
        outputButtonLayout.addWidget(self.toOutputButton)
        self.toOutputButton.setMaximumWidth(self.toOutputButton.
                                            sizeHint().height())
        self.toOutputButton.clicked.connect(self.fieldToOutput)
        self.delOutputButton = QPushButton('<<')
        outputButtonLayout.addWidget(self.delOutputButton)
        self.delOutputButton.setMaximumWidth(self.delOutputButton.
                                             sizeHint().height())
        self.delOutputButton.clicked.connect(self.delOutputField)

        outputBox = QGroupBox(_('Out&put Format'))
        topLayout.addWidget(outputBox, 2, 2)
        outputLayout = QVBoxLayout(outputBox)
        self.outputEdit = QTextEdit()
        self.outputEdit.setLineWrapMode(QTextEdit.NoWrap)
        outputLayout.addWidget(self.outputEdit)
        self.outputEdit.setTabChangesFocus(True)
        self.outputEdit.cursorPositionChanged.connect(self.
                                                      setControlAvailability)
        self.outputEdit.textChanged.connect(self.mainDialogRef.setModified)

        # advanced widgets
        otherBox = QGroupBox(_('Other Field References'))
        topLayout.addWidget(otherBox, 0, 2)
        self.advancedWidgets.append(otherBox)
        otherLayout = QHBoxLayout(otherBox)
        levelLayout =  QVBoxLayout()
        otherLayout.addLayout(levelLayout)
        levelLayout.setSpacing(0)
        levelLabel = QLabel(_('Reference Le&vel'))
        levelLayout.addWidget(levelLabel)
        levelCombo = QComboBox()
        levelLayout.addWidget(levelCombo)
        levelLabel.setBuddy(levelCombo)
        levelCombo.addItems(_refLevelList)
        levelCombo.currentIndexChanged.connect(self.changeRefLevel)
        refTypeLayout = QVBoxLayout()
        otherLayout.addLayout(refTypeLayout)
        refTypeLayout.setSpacing(0)
        refTypeLabel = QLabel(_('Refere&nce Type'))
        refTypeLayout.addWidget(refTypeLabel)
        self.refTypeCombo = QComboBox()
        refTypeLayout.addWidget(self.refTypeCombo)
        refTypeLabel.setBuddy(self.refTypeCombo)
        self.refTypeCombo.currentIndexChanged.connect(self.changeRefType)

        topLayout.setRowStretch(1, 1)
        topLayout.setRowStretch(2, 1)

    def updateContent(self):
        """Update page contents from current format settings.
        """
        typeNames = ConfigDialog.formatsRef.typeNames()
        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItems(typeNames)
        self.typeCombo.setCurrentIndex(typeNames.index(ConfigDialog.
                                                       currentTypeName))
        self.typeCombo.blockSignals(False)

        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        self.updateFieldList()
        self.titleEdit.blockSignals(True)
        self.titleEdit.setText(currentFormat.getTitleLine())
        self.titleEdit.end(False)
        self.titleEdit.blockSignals(False)
        self.outputEdit.blockSignals(True)
        self.outputEdit.setPlainText('\n'.join(currentFormat.getOutputLines()))
        cursor = self.outputEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.outputEdit.setTextCursor(cursor)
        self.outputEdit.blockSignals(False)

        self.refTypeCombo.blockSignals(True)
        self.refTypeCombo.clear()
        self.refTypeCombo.addItems(typeNames)
        refLevelType = (self.refLevelType if self.refLevelType else
                        ConfigDialog.currentTypeName)
        try:
            self.refTypeCombo.setCurrentIndex(typeNames.index(refLevelType))
        except ValueError:   # type no longer exists
            self.refLevelType = ConfigDialog.currentTypeName
            self.refTypeCombo.setCurrentIndex(typeNames.index(self.
                                                              refLevelType))
        self.refTypeCombo.blockSignals(False)
        self.setControlAvailability()

    def updateFieldList(self):
        """Reload the field list box.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        if not self.refLevelFlag:
            activeFormat = currentFormat
        elif self.refLevelFlag == '!':
            activeFormat = ConfigDialog.formatsRef.fileInfoFormat
        elif self.refLevelFlag == '#':
            activeFormat = nodeformat.DescendantCountFormat()
        else:
            try:
                activeFormat = ConfigDialog.formatsRef[self.refLevelType]
            except (KeyError, ValueError):
                self.refLevelType = ConfigDialog.currentTypeName
                activeFormat = currentFormat
        self.fieldListBox.blockSignals(True)
        self.fieldListBox.clear()
        for field in activeFormat.fields():
            if field.showInDialog:
                typeName = fieldformat.translatedTypeName(field.typeName)
                QTreeWidgetItem(self.fieldListBox, [field.name, typeName])
        selectList = self.fieldListBox.findItems(ConfigDialog.currentFieldName,
                                                 Qt.MatchFixedString |
                                                 Qt.MatchCaseSensitive)
        selectItem = (selectList[0] if selectList else
                      self.fieldListBox.topLevelItem(0))
        self.fieldListBox.setCurrentItem(selectItem)
        selectItem.setSelected(True)
        self.fieldListBox.setColumnWidth(0, self.fieldListBox.width() // 2)
        self.fieldListBox.blockSignals(False)

    def changeField(self):
        """Change the current format field based on a tree widget signal.

        Not set if a special field ref level is active.
        """
        selectList = self.fieldListBox.selectedItems()
        if (not self.refLevelFlag and len(selectList) == 1):
            ConfigDialog.currentFieldName = selectList[0].text(0)
        self.setControlAvailability()

    def setControlAvailability(self):
        """Set controls available based on text cursor movements.
        """
        fieldsSelected = len(self.fieldListBox.selectedItems()) > 0
        cursorInTitleField = self.isCursorInTitleField()
        self.toTitleButton.setEnabled(cursorInTitleField == None and
                                      fieldsSelected)
        self.delTitleButton.setEnabled(cursorInTitleField == True)
        cursorInOutputField = self.isCursorInOutputField()
        self.toOutputButton.setEnabled(cursorInOutputField == None and
                                       fieldsSelected)
        self.delOutputButton.setEnabled(cursorInOutputField == True)
        self.refTypeCombo.setEnabled(self.refLevelFlag not in ('', '!', '#'))

    def fieldToTitle(self):
        """Add selected field to cursor pos in title editor.
        """
        self.titleEdit.insert(self.selectedFieldSepNames(' '))
        self.titleEdit.setFocus()

    def delTitleField(self):
        """Remove field from cursor pos in title editor.
        """
        if self.isCursorInTitleField(True):
            self.titleEdit.insert('')

    def fieldToOutput(self):
        """Add selected field to cursor pos in output editor.
        """
        self.outputEdit.insertPlainText(self.selectedFieldSepNames())
        self.outputEdit.setFocus()

    def delOutputField(self):
        """Remove field from cursor pos in output editor.
        """
        if self.isCursorInOutputField(True):
            self.outputEdit.insertPlainText('')

    def selectedFieldSepNames(self, sep='\n'):
        """Return selected field name(s) with proper separators.

        Adjusts for special field ref levels.
        Multiple selections result in fields joined with the separator.
        Arguments:
            sep -- the separator to join multiple fields.
        """
        fields = ['{{*{0}{1}*}}'.format(self.refLevelFlag, item.text(0)) for
                  item in self.fieldListBox.selectedItems()]
        return '\n'.join(fields)

    def isCursorInTitleField(self, selectField=False):
        """Return True if a field pattern encloses the cursor/selection.

        Return False if the selection overlaps a field.
        Return None if there is no field at the cursor.
        Arguments:
            selectField -- select the entire field pattern if True.
        """
        cursorPos = self.titleEdit.cursorPosition()
        selectStart = self.titleEdit.selectionStart()
        if selectStart < 0:
            selectStart = cursorPos
        elif selectStart == cursorPos:   # backward selection
            cursorPos += len(self.titleEdit.selectedText())
        fieldPos = self.fieldPosAtCursor(selectStart, cursorPos,
                                         self.titleEdit.text())
        if not fieldPos:
            return None
        start, end = fieldPos
        if start == None or end == None:
            return False
        if selectField:
            self.titleEdit.setSelection(start, end - start)
        return True

    def isCursorInOutputField(self, selectField=False):
        """Return True if a field pattern encloses the cursor/selection.

        Return False if the selection overlaps a field.
        Return None if there is no field at the cursor.
        Arguments:
            selectField -- select the entire field pattern if True.
        """
        outputCursor = self.outputEdit.textCursor()
        selectStart = outputCursor.anchor()
        cursorPos = outputCursor.position()
        block = outputCursor.block()
        blockStart = block.position()
        if selectStart < blockStart or (selectStart > blockStart +
                                        block.length()):
            return False      # multi-line selection
        fieldPos = self.fieldPosAtCursor(selectStart - blockStart,
                                         cursorPos - blockStart, block.text())
        if not fieldPos:
            return None
        start, end = fieldPos
        if start == None or end == None:
            return False
        if selectField:
            outputCursor.setPosition(start + blockStart)
            outputCursor.setPosition(end + blockStart,
                                     QTextCursor.KeepAnchor)
            self.outputEdit.setTextCursor(outputCursor)
        return True

    def fieldPosAtCursor(self, anchorPos, cursorPos, textLine):
        """Find the position of the field pattern that encloses the selection.

        Return a tuple of (start, end) positions of the field if found.
        Return (start, None) or (None, end) if the selection overlaps.
        Return None if no field is found.
        Arguments:
            anchorPos -- the selection start
            cursorPos -- the selection end
            textLine -- the text to search
        """
        for match in fieldPattern.finditer(textLine):
            start = (match.start() if match.start() < anchorPos < match.end()
                     else None)
            end = (match.end() if match.start() < cursorPos < match.end()
                   else None)
            if start != None or end != None:
                return (start, end)
        return None

    def changeRefLevel(self, num):
        """Change other field ref level based on a combobox signal.

        Arguments:
            num -- the combobox index selected
        """
        self.refLevelFlag = _refLevelFlags[num]
        if self.refLevelFlag in ('', '!', '#'):
            self.refLevelType = None
        elif not self.refLevelType:
            self.refLevelType = ConfigDialog.currentTypeName
        self.updateFieldList()
        self.setControlAvailability()

    def changeRefType(self, num):
        """Change the other field ref level type based on a combobox signal.

        Arguments:
            num -- the combobox index selected
        """
        self.refLevelType = ConfigDialog.formatsRef.typeNames()[num]
        self.updateFieldList()
        self.setControlAvailability()

    def readChanges(self):
        """Make changes to the format for each widget.
        """
        currentFormat = ConfigDialog.formatsRef[ConfigDialog.currentTypeName]
        currentFormat.changeTitleLine(self.titleEdit.text())
        currentFormat.changeOutputLines(self.outputEdit.toPlainText().strip().
                                        split('\n'),
                                        not currentFormat.formatHtml)


class TitleEdit(QLineEdit):
    """LineEdit that avoids changing the selection on focus changes.
    """
    focusIn = pyqtSignal(QWidget)
    def __init__(self, parent=None):
        """Initialize the config dialog page.

        Arguments:
            parent -- the parent dialog
        """
        super().__init__(parent)

    def focusInEvent(self, event):
        """Override to keep selection & cursor position.

        Arguments:
            event -- the focus event
        """
        cursorPos = self.cursorPosition()
        selectStart = self.selectionStart()
        if selectStart == cursorPos:
            selectStart = cursorPos + len(self.selectedText())
        super().focusInEvent(event)
        self.setCursorPosition(cursorPos)
        if selectStart >= 0:
            self.setSelection(selectStart, cursorPos - selectStart)
        self.focusIn.emit(self)

    def focusOutEvent(self, event):
        """Override to keep selection & cursor position.

        Arguments:
            event -- the focus event
        """
        cursorPos = self.cursorPosition()
        selectStart = self.selectionStart()
        if selectStart == cursorPos:
            selectStart = cursorPos + len(self.selectedText())
        super().focusOutEvent(event)
        self.setCursorPosition(cursorPos)
        if selectStart >= 0:
            self.setSelection(selectStart, cursorPos - selectStart)


class TypeLimitCombo(QComboBox):
    """A combo box for selecting limited child types.
    """
    limitChanged = pyqtSignal()
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.checkBoxDialog = None
        self.typeNames = []
        self.selectSet = set()

    def updateLists(self, typeNames, selectSet):
        """Update control text and store data for popup.

        Arguments:
            typeNames -- a list of available type names
            selectSet -- a set of seleected type names
        """
        self.typeNames = typeNames
        self.updateSelects(selectSet)

    def updateSelects(self, selectSet):
        """Update control text and store selected items.

        Arguments:
            selectSet -- a set of seleected type names
        """
        self.selectSet = selectSet
        if not selectSet or selectSet == set(self.typeNames):
            text = _('[All Types Available]')
            self.selectSet = set()
        else:
            text = ', '.join(sorted(selectSet))
        self.addItem(text)
        self.setCurrentText(text)

    def showPopup(self):
        """Override to show a popup entry widget in place of a list view.
        """
        self.checkBoxDialog = TypeLimitCheckBox(self.typeNames,
                                                self.selectSet, self)
        self.checkBoxDialog.setMinimumWidth(self.width())
        self.checkBoxDialog.buttonChanged.connect(self.updateFromButton)
        self.checkBoxDialog.show()
        pos = self.mapToGlobal(self.rect().bottomRight())
        pos.setX(pos.x() - self.checkBoxDialog.width() + 1)
        screenBottom =  (QApplication.desktop().screenGeometry(self).
                         bottom())
        if pos.y() + self.checkBoxDialog.height() > screenBottom:
            pos.setY(pos.y() - self.rect().height() -
                     self.checkBoxDialog.height())
        self.checkBoxDialog.move(pos)

    def hidePopup(self):
        """Override to hide the popup entry widget.
        """
        if self.checkBoxDialog:
            self.checkBoxDialog.hide()
        super().hidePopup()

    def updateFromButton(self):
        """Update selected items based on a button change.
        """
        self.updateSelects(self.checkBoxDialog.selectSet())
        self.limitChanged.emit()


class TypeLimitCheckBox(QDialog):
    """A popup dialog box for selecting limited child types.
    """
    buttonChanged = pyqtSignal()
    def __init__(self, textList, selectSet, parent=None):
        """Initialize the combination dialog.

        Arguments:
            textList -- a list of text choices
            selectSet -- a set of choices to preselect
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        topLayout = QVBoxLayout(self)
        topLayout.setContentsMargins(0, 0, 0, 0)
        scrollArea = QScrollArea()
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        topLayout.addWidget(scrollArea)
        innerWidget = QWidget()
        innerLayout = QVBoxLayout(innerWidget)
        self.buttonGroup = QButtonGroup(self)
        self.buttonGroup.setExclusive(False)
        self.buttonGroup.buttonClicked.connect(self.buttonChanged)
        for text in textList:
            button = QCheckBox(text, innerWidget)
            if text in selectSet:
                button.setChecked(True)
            self.buttonGroup.addButton(button)
            innerLayout.addWidget(button)
        scrollArea.setWidget(innerWidget)
        buttons = self.buttonGroup.buttons()
        if buttons:
            buttons[0].setFocus()

    def selectSet(self):
        """Return a set of currently checked text.
        """
        result = set()
        for button in self.buttonGroup.buttons():
            if button.isChecked():
                result.add(button.text())
        return result

    def selectAll(self):
        """Select all of the entries.
        """
        for button in self.buttonGroup.buttons():
            button.setChecked(True)

    def selectNone(self):
        """Clear all of the selections.
        """
        for button in self.buttonGroup.buttons():
            button.setChecked(False)

    def contextMenuEvent(self, event):
        """Create a popup context menu.

        Arguments:
            event -- the menu even to process
        """
        menu = QMenu(self)
        menu.addAction(_('&Select All'), self.selectAll)
        menu.addAction(_('Select &None'), self.selectNone)
        menu.exec_(event.globalPos())


_illegalRe = re.compile(r'[^\w_\-.]')

class NameEntryDialog(QDialog):
    """Dialog to handle user entry of a type or field name.

    Restricts entry to alpha-numerics, underscores, dashes and periods.
    """
    def __init__(self, caption, labelText, defaultText='', addCheckBox = '',
                 badText=None, parent=None):
        """Initialize the name entry class.

        Arguments:
            caption -- the window title
            labelText -- text for a descriptive lable
            defaultText -- initial text
            addCheckBox -- the label for an extra check box if needed
            badText -- a set or list of other illegal strings
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.badText = set()
        if badText:
            self.badText = badText
        self.text = ''
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(caption)
        topLayout = QVBoxLayout(self)
        label = QLabel(labelText)
        topLayout.addWidget(label)
        self.entry = QLineEdit(defaultText)
        topLayout.addWidget(self.entry)
        self.entry.setFocus()
        self.entry.returnPressed.connect(self.accept)

        self.extraChecked = False
        if addCheckBox:
            self.extraCheckBox = QCheckBox(addCheckBox)
            topLayout.addWidget(self.extraCheckBox)
        else:
            self.extraCheckBox = None

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)

    def accept(self):
        """Check for acceptable string before closing.
        """
        self.text = self.entry.text().strip()
        if not self.text:
            error = _('The name cannot be empty')
        elif not self.text[0].isalpha():
            error = _('The name must start with a letter')
        elif self.text[:3].lower() == 'xml':
            error = _('The name cannot start with "xml"')
        elif ' ' in self.text:
            error = _('The name cannot contain spaces')
        elif _illegalRe.search(self.text):
            badChars = set(_illegalRe.findall(self.text))
            error = (_('The following characters are not allowed: {}').
                     format(''.join(badChars)))
        elif self.text in self.badText:
            error = _('The name was already used')
        else:
            if self.extraCheckBox:
                self.extraChecked = self.extraCheckBox.isChecked()
            return super().accept()
        QMessageBox.warning(self, 'TreeLine', error)


class IconSelectDialog(QDialog):
    """Dialog for selecting icons for a format type.
    """
    dialogSize = ()
    dialogPos = ()
    def __init__(self, nodeFormat, parent=None):
        """Create the icon select dialog.

        Arguments:
            nodeFormat -- the current node format to be set
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.currentIconName = nodeFormat.iconName
        if (not self.currentIconName or
            self.currentIconName not in globalref.treeIcons):
            self.currentIconName = icondict.defaultName
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Set Data Type Icon'))
        topLayout = QVBoxLayout(self)
        self.iconView = QListWidget()
        self.iconView.setViewMode(QListView.ListMode)
        self.iconView.setMovement(QListView.Static)
        self.iconView.setWrapping(True)
        self.iconView.setGridSize(QSize(112, 32))
        topLayout.addWidget(self.iconView)
        self.iconView.itemDoubleClicked.connect(self.accept)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        clearButton = QPushButton(_('Clear &Select'))
        ctrlLayout.addWidget(clearButton)
        clearButton.clicked.connect(self.iconView.clearSelection)
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        if IconSelectDialog.dialogSize:
            self.resize(IconSelectDialog.dialogSize[0],
                        IconSelectDialog.dialogSize[1])
            self.move(IconSelectDialog.dialogPos[0],
                      IconSelectDialog.dialogPos[1])
        self.loadIcons()

    def loadIcons(self):
        """Load icons from the icon dict source.
        """
        if not globalref.treeIcons.allLoaded:
            globalref.treeIcons.loadAllIcons()
        for name, icon in globalref.treeIcons.items():
            if icon:
                item = QListWidgetItem(icon, name, self.iconView)
                if name == self.currentIconName:
                    self.iconView.setCurrentItem(item)
        self.iconView.sortItems()
        selectedItem = self.iconView.currentItem()
        if selectedItem:
            self.iconView.scrollToItem(selectedItem,
                                      QAbstractItemView.PositionAtCenter)

    def saveSize(self):
        """Record dialog size at close.
        """
        IconSelectDialog.dialogSize = (self.width(), self.height())
        IconSelectDialog.dialogPos = (self.x(), self.y())

    def accept(self):
        """Save changes before closing.
        """
        selectedItems = self.iconView.selectedItems()
        if selectedItems:
            self.currentIconName = selectedItems[0].text()
            if self.currentIconName == icondict.defaultName:
                self.currentIconName = ''
        else:
            self.currentIconName = icondict.noneName
        self.saveSize()
        super().accept()

    def reject(self):
        """Save dialog size before closing.
        """
        self.saveSize()
        super().reject()


class SortKeyDialog(QDialog):
    """Dialog for defining sort key fields and directions.
    """
    directionNameDict = {True: _('forward'), False: _('reverse')}
    directionVarDict = dict([(name, boolVal) for boolVal, name in
                             directionNameDict.items()])
    def __init__(self, fieldDict, parent=None):
        """Create the sort key dialog.

        Arguments:
            fieldDict -- a dict of field names and values
            parent -- the parent overall dialog
        """
        super().__init__(parent)
        self.fieldDict = fieldDict
        self.numChanges = 0
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Sort Key Fields'))
        topLayout = QVBoxLayout(self)
        horizLayout = QHBoxLayout()
        topLayout.addLayout(horizLayout)
        fieldBox = QGroupBox(_('Available &Fields'))
        horizLayout.addWidget(fieldBox)
        boxLayout = QVBoxLayout(fieldBox)
        self.fieldListBox = QTreeWidget()
        boxLayout.addWidget(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setColumnCount(2)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type')])

        midButtonLayout = QVBoxLayout()
        horizLayout.addLayout(midButtonLayout)
        self.addFieldButton = QPushButton('>>')
        midButtonLayout.addWidget(self.addFieldButton)
        self.addFieldButton.setMaximumWidth(self.addFieldButton.
                                            sizeHint().height())
        self.addFieldButton.clicked.connect(self.addField)
        self.removeFieldButton = QPushButton('<<')
        midButtonLayout.addWidget(self.removeFieldButton)
        self.removeFieldButton.setMaximumWidth(self.removeFieldButton.
                                               sizeHint().height())
        self.removeFieldButton.clicked.connect(self.removeField)

        sortBox = QGroupBox(_('&Sort Criteria'))
        horizLayout.addWidget(sortBox)
        boxLayout = QVBoxLayout(sortBox)
        self.sortListBox = QTreeWidget()
        boxLayout.addWidget(self.sortListBox)
        self.sortListBox.setRootIsDecorated(False)
        self.sortListBox.setColumnCount(3)
        self.sortListBox.setHeaderLabels(['#', _('Field'), _('Direction')])
        self.sortListBox.currentItemChanged.connect(self.setControlsAvail)

        rightButtonLayout = QVBoxLayout()
        horizLayout.addLayout(rightButtonLayout)
        self.upButton = QPushButton(_('Move &Up'))
        rightButtonLayout.addWidget(self.upButton)
        self.upButton.clicked.connect(self.moveUp)
        self.downButton = QPushButton(_('&Move Down'))
        rightButtonLayout.addWidget(self.downButton)
        self.downButton.clicked.connect(self.moveDown)
        self.flipButton = QPushButton(_('Flip &Direction'))
        rightButtonLayout.addWidget(self.flipButton)
        self.flipButton.clicked.connect(self.flipDirection)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout)
        ctrlLayout.addStretch()
        self.okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(self.okButton)
        self.okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.updateContent()

    def updateContent(self):
        """Update dialog contents from current format settings.
        """
        sortFields = [field for field in self.fieldDict.values() if
                      field.sortKeyNum > 0]
        sortFields.sort(key = operator.attrgetter('sortKeyNum'))
        if not sortFields:
            sortFields = [list(self.fieldDict.values())[0]]
        self.fieldListBox.clear()
        for field in self.fieldDict.values():
            if field not in sortFields:
                QTreeWidgetItem(self.fieldListBox,
                                      [field.name, field.typeName])
        if self.fieldListBox.topLevelItemCount() > 0:
            self.fieldListBox.setCurrentItem(self.fieldListBox.topLevelItem(0))
        self.fieldListBox.setColumnWidth(0, self.fieldListBox.sizeHint().
                                         width() // 2)
        self.sortListBox.blockSignals(True)
        self.sortListBox.clear()
        for num, field in enumerate(sortFields, 1):
            sortDir = SortKeyDialog.directionNameDict[field.sortKeyForward]
            QTreeWidgetItem(self.sortListBox,
                                  [repr(num), field.name, sortDir])
        self.sortListBox.setCurrentItem(self.sortListBox.topLevelItem(0))
        self.sortListBox.blockSignals(False)
        self.sortListBox.setColumnWidth(0, self.sortListBox.sizeHint().
                                        width() // 8)
        self.setControlsAvail()

    def setControlsAvail(self):
        """Set controls available based on selections.
        """
        self.addFieldButton.setEnabled(self.fieldListBox.topLevelItemCount() >
                                       0)
        hasSortItems = self.sortListBox.topLevelItemCount() > 0
        self.removeFieldButton.setEnabled(hasSortItems)
        if hasSortItems:
            sortPosNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                              currentItem())
        self.upButton.setEnabled(hasSortItems and sortPosNum > 0)
        self.downButton.setEnabled(hasSortItems and sortPosNum <
                                   self.sortListBox.topLevelItemCount() - 1)
        self.flipButton.setEnabled(hasSortItems)
        self.okButton.setEnabled(hasSortItems)

    def addField(self):
        """Add a field to the sort criteria list.
        """
        itemNum = self.fieldListBox.indexOfTopLevelItem(self.fieldListBox.
                                                        currentItem())
        fieldName = self.fieldListBox.takeTopLevelItem(itemNum).text(0)
        field = self.fieldDict[fieldName]
        sortNum = self.sortListBox.topLevelItemCount() + 1
        sortDir = SortKeyDialog.directionNameDict[field.sortKeyForward]
        self.sortListBox.blockSignals(True)
        sortItem = QTreeWidgetItem(self.sortListBox,
                                         [repr(sortNum), fieldName, sortDir])
        self.sortListBox.setCurrentItem(sortItem)
        self.sortListBox.blockSignals(False)
        self.setControlsAvail()
        self.numChanges += 1

    def removeField(self):
        """Remove a field from the sort criteria list.
        """
        itemNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                       currentItem())
        self.sortListBox.blockSignals(True)
        fieldName = self.sortListBox.takeTopLevelItem(itemNum).text(1)
        self.renumberSortFields()
        self.sortListBox.blockSignals(False)
        field = self.fieldDict[fieldName]
        sortFieldNames = set()
        for num in range(self.sortListBox.topLevelItemCount()):
            sortFieldNames.add(self.sortListBox.topLevelItem(num).text(1))
        fieldList = [field for field in self.fieldDict.values() if
                     field.name not in sortFieldNames]
        pos = fieldList.index(field)
        fieldItem = QTreeWidgetItem([fieldName, field.typeName])
        self.fieldListBox.insertTopLevelItem(pos, fieldItem)
        self.setControlsAvail()
        self.numChanges += 1

    def moveUp(self):
        """Move a field upward in the sort criteria.
        """
        itemNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                       currentItem())
        self.sortListBox.blockSignals(True)
        sortItem = self.sortListBox.takeTopLevelItem(itemNum)
        self.sortListBox.insertTopLevelItem(itemNum - 1, sortItem)
        self.sortListBox.setCurrentItem(sortItem)
        self.renumberSortFields()
        self.sortListBox.blockSignals(False)
        self.setControlsAvail()
        self.numChanges += 1

    def moveDown(self):
        """Move a field downward in the sort criteria.
        """
        itemNum = self.sortListBox.indexOfTopLevelItem(self.sortListBox.
                                                       currentItem())
        self.sortListBox.blockSignals(True)
        sortItem = self.sortListBox.takeTopLevelItem(itemNum)
        self.sortListBox.insertTopLevelItem(itemNum + 1, sortItem)
        self.sortListBox.setCurrentItem(sortItem)
        self.renumberSortFields()
        self.sortListBox.blockSignals(False)
        self.setControlsAvail()
        self.numChanges += 1

    def flipDirection(self):
        """Toggle the direction of the current sort field.
        """
        sortItem = self.sortListBox.currentItem()
        oldDirection = SortKeyDialog.directionVarDict[sortItem.text(2)]
        newDirection = SortKeyDialog.directionNameDict[not oldDirection]
        sortItem.setText(2, newDirection)
        self.numChanges += 1

    def renumberSortFields(self):
        """Update field numbers in the sort list.
        """
        for num in range(self.sortListBox.topLevelItemCount()):
            self.sortListBox.topLevelItem(num).setText(0, repr(num + 1))

    def accept(self):
        """Save changes before closing.
        """
        if not self.numChanges:
            return self.reject()
        for field in self.fieldDict.values():
            field.sortKeyNum = 0
            field.sortKeyForward = True
        for num in range(self.sortListBox.topLevelItemCount()):
            fieldItem = self.sortListBox.topLevelItem(num)
            field = self.fieldDict[fieldItem.text(1)]
            field.sortKeyNum = num + 1
            field.sortKeyForward = SortKeyDialog.directionVarDict[fieldItem.
                                                                  text(2)]
        return super().accept()


_mathRefLevels = [_('Self Reference'), _('Parent Reference'),
                  _('Root Reference'), _('Child Reference'), _('Child Count')]
# _mathRefLevelFlags  correspond to _mathRefLevels
_mathRefLevelFlags = ['', '*', '$', '&', '#']
_mathResultTypes = [N_('Number Result'), N_('Date Result'), N_('Time Result'),
                    N_('Boolean Result'), N_('Text Result')]
_operatorTypes = [_('Arithmetic Operators'), _('Comparison Operators'),
                  _('Text Operators')]
_arithmeticOperators = [('+', _('add')),
                        ('-', _('subtract')),
                        ('*', _('multiply')),
                        ('/', _('divide')),
                        ('//', _('floor divide')),
                        ('%', _('modulus')),
                        ('**', _('power')),
                        ('sum()', _('sum of items')),
                        ('max()', _('maximum')),
                        ('min()', _('minimum')),
                        ('mean()', _('average')),
                        ('abs()', _('absolute value')),
                        ('sqrt()', _('square root')),
                        ('log()', _('natural logarithm')),
                        ('log10()', _('base-10 logarithm')),
                        ('factorial()', _('factorial')),
                        ('round()', _('round to num digits')),
                        ('floor()', _('lower integer')),
                        ('ceil()', _('higher integer')),
                        ('int()', _('truncated integer')),
                        ('float()', _('floating point')),
                        ('sin()', _('sine of radians')),
                        ('cos()', _('cosine of radians')),
                        ('tan()', _('tangent of radians')),
                        ('asin()', _('arc sine')),
                        ('acos()', _('arc cosine')),
                        ('atan()', _('arc tangent')),
                        ('degrees()', _('radians to degrees')),
                        ('radians()', _('degrees to radians')),
                        ('pi', _('pi constant')),
                        ('e', _('natural log constant'))]
_comparisonOperators = [('==', _('equal to')),
                        ('<', _('less than')),
                        ('>', _('greater than')),
                        ('<=', _('less than or equal to')),
                        ('>=', _('greater than or equal to')),
                        ('!=', _('not equal to')),
                        ('() if () else ()',
                         _('true value, condition, false value')),
                        ('and', _('logical and')),
                        ('or', _('logical or')),
                        ('startswith()',
                         _('true if 1st text arg starts with 2nd arg')),
                        ('endswith()',
                         _('true if 1st text arg ends with 2nd arg')),
                        ('contains()',
                         _('true if 1st text arg contains 2nd arg'))]
_textOperators = [('+', _('concatenate text')),
                  ("join(' ', )", _('join text using 1st arg as separator')),
                  ('upper()', _('convert text to upper case')),
                  ('lower()', _('convert text to lower case')),
                  ('replace()', _('in 1st arg, replace 2nd arg with 3rd arg'))]
# _operatorLists correspond to _operatorTypes
_operatorLists = [_arithmeticOperators, _comparisonOperators, _textOperators]

class MathEquationDialog(QDialog):
    """Dialog for defining equations for Math fields.
    """
    def __init__(self, nodeFormat, field, parent=None):
        """Create the math equation dialog.

        Arguments:
            nodeFormat -- the current node format
            field -- the Math field
        """
        super().__init__(parent)
        self.nodeFormat = nodeFormat
        self.typeFormats = self.nodeFormat.parentFormats
        self.field = field
        self.refLevelFlag = ''
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Define Math Field Equation'))

        topLayout = QGridLayout(self)
        fieldBox = QGroupBox(_('Field References'))
        topLayout.addWidget(fieldBox, 0, 0, 2, 1)
        fieldLayout = QVBoxLayout(fieldBox)
        innerLayout = QVBoxLayout()
        innerLayout.setSpacing(0)
        fieldLayout.addLayout(innerLayout)
        levelLabel = QLabel(_('Reference &Level'))
        innerLayout.addWidget(levelLabel)
        levelCombo = QComboBox()
        innerLayout.addWidget(levelCombo)
        levelLabel.setBuddy(levelCombo)
        levelCombo.addItems(_mathRefLevels)
        levelCombo.currentIndexChanged.connect(self.changeRefLevel)
        innerLayout = QVBoxLayout()
        innerLayout.setSpacing(0)
        fieldLayout.addLayout(innerLayout)
        typeLabel = QLabel(_('Reference &Type'))
        innerLayout.addWidget(typeLabel)
        self.typeCombo = QComboBox()
        innerLayout.addWidget(self.typeCombo)
        typeLabel.setBuddy(self.typeCombo)
        self.typeCombo.addItems(self.typeFormats.typeNames())
        self.typeCombo.currentIndexChanged.connect(self.updateFieldList)
        innerLayout = QVBoxLayout()
        innerLayout.setSpacing(0)
        fieldLayout.addLayout(innerLayout)
        fieldLabel = QLabel(_('Available &Field List'))
        innerLayout.addWidget(fieldLabel)
        self.fieldListBox = QTreeWidget()
        innerLayout.addWidget(self.fieldListBox)
        fieldLabel.setBuddy(self.fieldListBox)
        self.fieldListBox.setRootIsDecorated(False)
        self.fieldListBox.setColumnCount(2)
        self.fieldListBox.setHeaderLabels([_('Name'), _('Type')])

        resultTypeBox = QGroupBox(_('&Result Type'))
        topLayout.addWidget(resultTypeBox, 0, 1)
        resultTypeLayout = QVBoxLayout(resultTypeBox)
        self.resultTypeCombo = QComboBox()
        resultTypeLayout.addWidget(self.resultTypeCombo)
        self.resultTypeCombo.addItems([_(str) for str in _mathResultTypes])
        results = [s.split(' ', 1)[0].lower() for s in _mathResultTypes]
        resultStr = self.field.resultType.name
        self.resultTypeCombo.setCurrentIndex(results.index(resultStr))

        operBox = QGroupBox(_('Operations'))
        topLayout.addWidget(operBox, 1, 1)
        operLayout = QVBoxLayout(operBox)
        innerLayout = QVBoxLayout()
        innerLayout.setSpacing(0)
        operLayout.addLayout(innerLayout)
        operTypeLabel = QLabel(_('O&perator Type'))
        innerLayout.addWidget(operTypeLabel)
        operTypeCombo = QComboBox()
        innerLayout.addWidget(operTypeCombo)
        operTypeLabel.setBuddy(operTypeCombo)
        operTypeCombo.addItems(_operatorTypes)
        operTypeCombo.currentIndexChanged.connect(self.replaceOperatorList)
        innerLayout = QVBoxLayout()
        innerLayout.setSpacing(0)
        operLayout.addLayout(innerLayout)
        operListLabel = QLabel(_('Oper&ator List'))
        innerLayout.addWidget(operListLabel)
        self.operListBox = QTreeWidget()
        innerLayout.addWidget(self.operListBox)
        operListLabel.setBuddy(self.operListBox)
        self.operListBox.setRootIsDecorated(False)
        self.operListBox.setColumnCount(2)
        self.operListBox.setHeaderLabels([_('Name'), _('Description')])
        self.replaceOperatorList(0)

        buttonLayout = QHBoxLayout()
        topLayout.addLayout(buttonLayout, 2, 0)
        buttonLayout.addStretch()
        self.addFieldButton = QPushButton('\u25bc')
        buttonLayout.addWidget(self.addFieldButton)
        self.addFieldButton.setMaximumWidth(self.addFieldButton.
                                            sizeHint().height())
        self.addFieldButton.clicked.connect(self.addField)
        self.delFieldButton = QPushButton('\u25b2')
        buttonLayout.addWidget(self.delFieldButton)
        self.delFieldButton.setMaximumWidth(self.delFieldButton.
                                            sizeHint().height())
        self.delFieldButton.clicked.connect(self.deleteField)
        buttonLayout.addStretch()

        buttonLayout = QHBoxLayout()
        topLayout.addLayout(buttonLayout, 2, 1)
        self.addOperButton = QPushButton('\u25bc')
        buttonLayout.addWidget(self.addOperButton)
        self.addOperButton.setMaximumWidth(self.addOperButton.
                                           sizeHint().height())
        self.addOperButton.clicked.connect(self.addOperator)

        equationBox = QGroupBox(_('&Equation'))
        topLayout.addWidget(equationBox, 3, 0, 1, 2)
        equationLayout = QVBoxLayout(equationBox)
        self.equationEdit = TitleEdit()
        equationLayout.addWidget(self.equationEdit)
        self.equationEdit.setText(self.field.equationText())
        self.equationEdit.cursorPositionChanged.connect(self.
                                                        setControlAvailability)

        ctrlLayout = QHBoxLayout()
        topLayout.addLayout(ctrlLayout, 4, 0, 1, 2)
        ctrlLayout.addStretch()
        okButton = QPushButton(_('&OK'))
        ctrlLayout.addWidget(okButton)
        okButton.setDefault(True)
        okButton.clicked.connect(self.accept)
        cancelButton = QPushButton(_('&Cancel'))
        ctrlLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.changeRefLevel(0)
        self.equationEdit.setFocus()

    def updateFieldList(self):
        """Update field list based on reference type setting.
        """
        currentFormat = self.typeFormats[self.typeCombo.currentText()]
        self.fieldListBox.clear()
        if self.refLevelFlag != '#':
            for field in currentFormat.fields():
                if (hasattr(field, 'mathValue') and field.showInDialog
                    and (self.refLevelFlag or field != self.field)):
                    QTreeWidgetItem(self.fieldListBox,
                                    [field.name, _(field.typeName)])
        else:
            QTreeWidgetItem(self.fieldListBox, [_('Count'),
                                                _('Number of Children')])
        if self.fieldListBox.topLevelItemCount():
            selectItem = self.fieldListBox.topLevelItem(0)
            self.fieldListBox.setCurrentItem(selectItem)
            selectItem.setSelected(True)
        self.fieldListBox.resizeColumnToContents(0)
        self.fieldListBox.setColumnWidth(0,
                                         self.fieldListBox.columnWidth(0) * 2)
        self.setControlAvailability()

    def setControlAvailability(self):
        """Set controls available based on text cursor movements.
        """
        cursorInField = self.isCursorInField()
        fieldCount = self.fieldListBox.topLevelItemCount()
        self.addFieldButton.setEnabled(cursorInField == None and fieldCount)
        self.delFieldButton.setEnabled(cursorInField == True)
        self.addOperButton.setEnabled(cursorInField == None)

    def addField(self):
        """Add selected field to cursor pos in the equation editor.
        """
        fieldSepName = '{{*{0}{1}*}}'.format(self.refLevelFlag,
                                             self.fieldListBox.currentItem().
                                             text(0))
        self.equationEdit.insert(fieldSepName)
        self.equationEdit.setFocus()

    def deleteField(self):
        """Remove field from cursor pos in the equation editor.
        """
        if self.isCursorInField(True):
            self.equationEdit.insert('')
        self.equationEdit.setFocus()

    def addOperator(self):
        """Add selected operator to cursor pos in the equation editor.
        """
        oper = self.operListBox.currentItem().text(0)
        origText = self.equationEdit.text()
        cursorPos = self.equationEdit.cursorPosition()
        if cursorPos != 0 and origText[cursorPos - 1] != ' ':
            oper = ' ' + oper
        self.equationEdit.insert(oper + ' ')
        parenPos = oper.find(')')
        if parenPos >= 0:
            cursorPos = self.equationEdit.cursorPosition()
            self.equationEdit.setCursorPosition(cursorPos - len(oper) +
                                                parenPos - 1)
        self.equationEdit.setFocus()

    def isCursorInField(self, selectField=False):
        """Return True if a field pattern encloses the cursor/selection.

        Return False if the selection overlaps a field.
        Return None if there is no field at the cursor.
        Arguments:
            selectField -- select the entire field pattern if True.
        """
        cursorPos = self.equationEdit.cursorPosition()
        selectStart = self.equationEdit.selectionStart()
        if selectStart < 0:
            selectStart = cursorPos
        elif selectStart == cursorPos:   # backward selection
            cursorPos += len(self.equationEdit.selectedText())
        start = end = None
        for match in fieldPattern.finditer(self.equationEdit.text()):
            start = (match.start() if match.start() < selectStart < match.end()
                     else None)
            end = (match.end() if match.start() < cursorPos < match.end()
                   else None)
            if start != None or end != None:
                break
        if start == None and end == None:
            return None
        if start == None or end == None:
            return False
        if selectField:
            self.equationEdit.setSelection(start, end - start)
        return True

    def changeRefLevel(self, num):
        """Change the reference level based on a combobox signal.

        Arguments:
            num -- the combobox index selected
        """
        self.refLevelFlag = _mathRefLevelFlags[num]
        if self.refLevelFlag in ('', '#'):
            self.typeCombo.setEnabled(False)
            self.typeCombo.setCurrentIndex(self.typeFormats.typeNames().
                                           index(self.nodeFormat.name))
        else:
            self.typeCombo.setEnabled(True)
        self.updateFieldList()

    def replaceOperatorList(self, num):
        """Change the operator list based on a signal from the oper type combo.

        Arguments:
            num -- the combobox index selected
        """
        self.operListBox.clear()
        for oper, descr in _operatorLists[num]:
            QTreeWidgetItem(self.operListBox, [oper, descr])
        self.operListBox.resizeColumnToContents(0)
        self.operListBox.setColumnWidth(0, int(self.operListBox.columnWidth(0)
                                               * 1.2))
        self.operListBox.resizeColumnToContents(1)
        selectItem = self.operListBox.topLevelItem(0)
        self.operListBox.setCurrentItem(selectItem)
        selectItem.setSelected(True)

    def accept(self):
        """Verify the equation and close the dialog if acceptable.
        """
        eqnText = self.equationEdit.text().strip()
        if eqnText:
            eqn = matheval.MathEquation(eqnText)
            try:
                eqn.validate()
            except ValueError as err:
                QMessageBox.warning(self, 'TreeLine',
                                    _('Equation error: {}').format(err))
                return
            self.typeFormats.emptiedMathDict.setdefault(self.nodeFormat.name,
                                                set()).discard(self.field.name)
            self.field.equation = eqn
        else:
            if self.field.equationText():
                self.typeFormats.emptiedMathDict.setdefault(self.nodeFormat.
                                              name, set()).add(self.field.name)
            self.field.equation = None
        resultStr = (_mathResultTypes[self.resultTypeCombo.currentIndex()].
                     split(' ', 1)[0].lower())
        self.field.changeResultType(fieldformat.MathResult[resultStr])
        super().accept()
