#!/usr/bin/env python3

#******************************************************************************
# undo.py, provides a classes to store and execute undo & redo operations
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import copy
import treenode
import globalref


class UndoRedoList(list):
    """Stores undo or redo objects.
    """
    def __init__(self, action, localControlRef):
        """Initialize the undo or redo storage.

        Set the number of stored levels based on the user option.
        Arguments:
            action -- the Qt action for undo/redo menus
            localControlRef -- ref control class for selections, modified, etc.
        """
        super().__init__()
        self.action = action
        self.action.setEnabled(False)
        self.localControlRef = localControlRef
        self.levels = globalref.genOptions.getValue('UndoLevels')
        self.altListRef = None   # holds a ref to redo or undo list

    def addUndoObj(self, undoObject, clearRedo=True):
        """Add the given undo or redo object to the list.

        Arguments:
            undoObject -- the object to be added
            clearRedo -- if true, clear redo list (can't redo after changes)
        """
        self.append(undoObject)
        del self[:-self.levels]
        if self.levels == 0:
            del self[:]
        self.action.setEnabled(len(self) > 0)
        if clearRedo and self.altListRef:
            self.altListRef.clearList()

    def clearList(self):
        """Empty the undo/redo list, primarily for no redo after a change.
        """
        del self[:]
        self.action.setEnabled(False)

    def removeLastUndo(self, undoObject):
        """Remove the last undo object if it matches the given object.

        Arguments:
            undoObject -- the object to be removed
        """
        if self[-1] is undoObject:
            del self[-1]
            self.action.setEnabled(len(self) > 0)

    def undo(self):
        """Save current state to altListRef and restore the last saved state.

        Remove the last undo item from the list.
        Restore the previous selection and saved doc modified state.
        """
        item = self.pop()
        item.undo(self.altListRef)
        self.localControlRef.currentSelectionModel().\
                             selectNodes(item.selectedNodes, False)
        self.localControlRef.setModified(item.modified)
        self.action.setEnabled(len(self) > 0)


class UndoBase:
    """Abstract base class for undo objects.
    """
    def __init__(self, localControlRef):
        """Initialize data storage, selected nodes and doc modified status.

        Arguments:
            selectedNodes -- list of currently selected nodes
            modified -- the current doc modified status
        """
        self.dataList = []
        self.selectedNodes = (localControlRef.currentSelectionModel().
                              selectedNodes())
        self.modified = localControlRef.modified


class DataUndo(UndoBase):
    """Info for undo/redo of tree node data changes.
    """
    def __init__(self, listRef, nodes, skipSame=False, fieldRef='',
                 notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a node or a list of nodes to back up
            skipSame -- if true, don't add an undo that is similar to the last
            fieldRef -- optional field name ref to check for similar changes
            notRedo -- if True, add clones and clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if isinstance(nodes, treenode.TreeNode):
            nodes = [nodes]
        if notRedo:
            for node in nodes[:]:
                nodes.extend(list(node.cloneGen()))
        if (skipSame and listRef and isinstance(listRef[-1], DataUndo) and
            len(listRef[-1].dataList) ==
            1 + len(listRef[-1].dataList[0][0].clones) and
            len(nodes) == 1 + len(nodes[0].clones) and
            nodes[0] == listRef[-1].dataList[0][0] and
            fieldRef == listRef[-1].dataList[0][2]):
            return
        for node in nodes:
            self.dataList.append((node, node.data.copy(), fieldRef,
                                  node.uniqueId, node.clones.copy()))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            DataUndo(redoRef, [data[0] for data in self.dataList],
                     False, '', False)
        for node, data, fieldRef, uniqueId, clones in self.dataList:
            node.data = data
            if node.uniqueId != uniqueId:
                node.removeUniqueId()
                node.uniqueId = uniqueId
                node.resetUniqueId()
            node.clones = clones
        for items in self.dataList:
            node = items[0]
            node.updateCloneLinks()


class ChildListUndo(UndoBase):
    """Info for undo/redo of tree node child lists.
    """
    def __init__(self, listRef, nodes, skipSame=False, notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a parent node or a list of parents to save children
            skipSame -- if true, don't add an undo that is similar to the last
            notRedo -- if True, add clones and clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if isinstance(nodes, treenode.TreeNode):
            nodes = [nodes]
        if notRedo:
            for node in nodes[:]:
                nodes.extend(list(node.cloneGen()))
        if (skipSame and listRef and isinstance(listRef[-1], ChildListUndo)
            and len(listRef[-1].dataList) == 1 and len(nodes) == 1 and
            nodes[0] == listRef[-1].dataList[0][0]):
            return
        for node in nodes:
            self.dataList.append((node, node.childList[:]))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            ChildListUndo(redoRef, [data[0] for data in self.dataList],
                          False, False)
        for node, childList in self.dataList:
            for oldNode in node.childList:
                if oldNode not in childList and (oldNode.parent == node or
                                                 not oldNode.parent):
                    oldNode.removeUniqueId()
            node.childList = childList
            for child in childList:
                child.parent = node
                for grandchild in child.descendantGen():
                    grandchild.resetUniqueId()
        for node, childList in self.dataList:
            for child in childList:
                for grandchild in child.descendantGen():
                    grandchild.updateCloneLinks()


class TypeUndo(UndoBase):
    """Info for undo/redo of tree node type name changes.

    Also saves node data to cover blank node title replacement and
    initial data settings.
    """
    def __init__(self, listRef, nodes, notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a node or a list of nodes to back up
            notRedo -- if True, add clones and clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if isinstance(nodes, treenode.TreeNode):
            nodes = [nodes]
        if notRedo:
            for node in nodes[:]:
                nodes.extend(list(node.cloneGen()))
        for node in nodes:
            self.dataList.append((node, node.formatName, node.data.copy(),
                                  node.uniqueId, node.clones.copy()))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            TypeUndo(redoRef, [data[0] for data in self.dataList], False)
        for node, formatName, data, uniqueId, clones in self.dataList:
            node.formatName = formatName
            node.data = data
            if node.uniqueId != uniqueId:
                node.removeUniqueId()
                node.uniqueId = uniqueId
                node.resetUniqueId()
            node.clones = clones
        for items in self.dataList:
            node = items[0]
            node.updateCloneLinks()


class FormatUndo(UndoBase):
    """Info for undo/redo of tree node type format changes.
    """
    def __init__(self, listRef, origTreeFormats, newTreeFormats,
                 notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            origTreeFormats -- the format data to store
            newTreeFormats -- the replacement format, contains rename dicts
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        self.treeFormats = copy.deepcopy(origTreeFormats)
        self.modelRef = listRef.localControlRef.model
        self.treeFormats.fieldRenameDict = {}
        for typeName, fieldDict in newTreeFormats.fieldRenameDict.items():
            self.treeFormats.fieldRenameDict[typeName] = {}
            for oldName, newName in fieldDict.items():
                self.treeFormats.fieldRenameDict[typeName][newName] = oldName
        self.treeFormats.typeRenameDict = {}
        for oldName, newName in newTreeFormats.typeRenameDict.items():
            self.treeFormats.typeRenameDict[newName] = oldName
            if newName in self.treeFormats.fieldRenameDict:
                self.treeFormats.fieldRenameDict[oldName] = (self.treeFormats.
                                                      fieldRenameDict[newName])
                del self.treeFormats.fieldRenameDict[newName]
        self.treeFormats.changedIdFieldTypes = set()
        for typeObj in newTreeFormats.changedIdFieldTypes:
            try:
                self.treeFormats.changedIdFieldTypes.add(self.
                                                         treeFormats[typeObj.
                                                                     name])
            except KeyError:   # not needed for new tree formats
                pass
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            FormatUndo(redoRef, self.modelRef.formats, self.treeFormats, False)
        self.modelRef.configDialogFormats = self.treeFormats
        self.modelRef.applyConfigDialogFormats(False)
        dialog = globalref.mainControl.configDialog
        if dialog and dialog.isVisible():
            dialog.reset()


class BranchUndo(UndoBase):
    """Info for undo/redo of full tree branches.

    Includes all node data and child lists.
    """
    def __init__(self, listRef, nodes, notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a node or a list of nodes to save children
            notRedo -- if True, add clones and clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if isinstance(nodes, treenode.TreeNode):
            nodes = [nodes]
        if notRedo:
            for node in nodes[:]:
                nodes.extend(list(node.cloneGen()))
        self.modelRef = listRef.localControlRef.model
        for parent in nodes:
            for node in parent.descendantGen():
                self.dataList.append((node, node.data.copy(),
                                      node.childList[:], node.uniqueId,
                                      node.clones.copy()))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            BranchUndo(redoRef, [data[0] for data in self.dataList], False)
        for node, data, childList, uniqueId, clones in self.dataList:
            for oldNode in node.childList:
                if oldNode not in childList and (oldNode.parent == node or
                                                 not oldNode.parent):
                    oldNode.removeUniqueId()
            node.data = data
            node.childList = childList
            for child in childList:
                child.parent = node
            if node.uniqueId != uniqueId:
                node.removeUniqueId()
                node.uniqueId = uniqueId
            node.resetUniqueId()
            node.clones = clones
        for items in self.dataList:
            node = items[0]
            node.updateCloneLinks()


class BranchFormatUndo(UndoBase):
    """Info for undo/redo of full tree branches and formats.

    Includes all node data, child lists, and full tree format.
    """
    def __init__(self, listRef, nodes, treeFormats, notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a node or a list of nodes to save children
            treeFormats -- the format data to store
            notRedo -- if True, add clones and clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if isinstance(nodes, treenode.TreeNode):
            nodes = [nodes]
        if notRedo:
            for node in nodes[:]:
                nodes.extend(list(node.cloneGen()))
        self.treeFormats = copy.deepcopy(treeFormats)
        self.modelRef = listRef.localControlRef.model
        for parent in nodes:
            for node in parent.descendantGen():
                self.dataList.append((node, node.data.copy(),
                                      node.childList[:], node.uniqueId,
                                      node.clones.copy()))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            BranchFormatUndo(redoRef, [data[0] for data in self.dataList],
                             self.modelRef.formats, False)
        self.modelRef.formats = self.treeFormats
        self.modelRef.getConfigDialogFormats(True)
        dialog = globalref.mainControl.configDialog
        if dialog and dialog.isVisible():
            dialog.reset()
        for node, data, childList, uniqueId, clones in self.dataList:
            for oldNode in node.childList:
                if oldNode not in childList and (oldNode.parent == node or
                                                 not oldNode.parent):
                    oldNode.removeUniqueId()
            node.data = data
            node.childList = childList
            for child in childList:
                child.parent = node
            if node.uniqueId != uniqueId:
                node.removeUniqueId()
                node.uniqueId = uniqueId
            node.resetUniqueId()
            node.clones = clones
        for items in self.dataList:
            node = items[0]
            node.updateCloneLinks()


class ParamUndo(UndoBase):
    """Info for undo/redo of any variable parameter.
    """
    def __init__(self, listRef, varList, notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            varList - list of tuples, variable's owner and variable's name
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        for varOwner, varName in varList:
            value = varOwner.__dict__[varName]
            self.dataList.append((varOwner, varName, value))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            ParamUndo(redoRef, [item[:2] for item in self.dataList], False)
        for varOwner, varName, value in self.dataList:
            varOwner.__dict__[varName] = value


class StateSettingUndo(UndoBase):
    """Info for undo/redo of objects with get/set functions for attributes.
    """
    def __init__(self, listRef, getFunction, setFunction, notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            getFunction -- a function ref that returns a state variable
            setFunction -- a function ref that restores from the state varible
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        self.getFunction = getFunction
        self.setFunction = setFunction
        self.data = getFunction()
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            StateSettingUndo(redoRef, self.getFunction, self.setFunction,
                             False)
        self.setFunction(self.data)
