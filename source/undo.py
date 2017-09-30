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
        self.levels = globalref.genOptions['UndoLevels']
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
        # # clear selection to avoid crash due to invalid selection:
        # self.localControlRef.currentSelectionModel().selectSpots([], False)
        item = self.pop()
        item.undo(self.altListRef)
        selectSpots = [node.spotByNumber(num) for (node, num) in
                       item.selectedTuples]
        self.localControlRef.currentSelectionModel().selectSpots(selectSpots,
                                                                 False)
        self.localControlRef.setModified(item.modified)
        self.action.setEnabled(len(self) > 0)


class UndoBase:
    """Abstract base class for undo objects.
    """
    def __init__(self, localControlRef):
        """Initialize data storage, selected nodes and doc modified status.

        Arguments:
            localControlRef -- ref control class for selections, modified, etc.
        """
        self.dataList = []
        self.treeStructRef = localControlRef.structure
        self.selectedTuples = [(spot.nodeRef, spot.instanceNumber())
                               for spot in
                               localControlRef.currentSelectionModel().
                               selectedSpots()]
        self.modified = localControlRef.modified


class DataUndo(UndoBase):
    """Info for undo/redo of tree node data changes.
    """
    def __init__(self, listRef, nodes, addChildren=False, addBranch=False,
                 skipSame=False, fieldRef='', notRedo=True):
        """Create the data undo class and add it to the undoStore.

        Can't use skipSame if addChildren or addBranch are True.
        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a node or a list of nodes to back up
            addChildren -- if True, include child nodes
            addBranch -- if True, include all branch nodes (ignores addChildren
            skipSame -- if true, don't add an undo that is similar to the last
            fieldRef -- optional field name ref to check for similar changes
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if not isinstance(nodes, list):
            nodes = [nodes]
        if (skipSame and listRef and isinstance(listRef[-1], DataUndo) and
            len(listRef[-1].dataList) == 1 and len(nodes) == 1 and
            nodes[0] == listRef[-1].dataList[0][0] and
            fieldRef == listRef[-1].dataList[0][2]):
            return
        for node in nodes:
            if addBranch:
                for child in node.descendantGen():
                    self.dataList.append((child, child.data.copy(), ''))
            else:
                self.dataList.append((node, node.data.copy(), fieldRef))
                if addChildren:
                    for child in node.childList:
                        self.dataList.append((child, child.data.copy(), ''))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            DataUndo(redoRef, [data[0] for data in self.dataList], False,
                     False, False, '', False)
        for node, data, fieldRef in self.dataList:
            node.data = data


class ChildListUndo(UndoBase):
    """Info for undo/redo of tree node child lists.
    """
    def __init__(self, listRef, nodes, addChildren=False, addBranch=False,
                 treeFormats=None, skipSame=False, notRedo=True):
        """Create the child list undo class and add it to the undoStore.

        Also stores data formats if given.
        Can't use skipSame if addChildren or addBranch are True.
        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a parent node or a list of parents to save children
            addChildren -- if True, include child nodes
            addBranch -- if True, include all branch nodes (ignores addChildren
            treeFormats -- the format data to store
            skipSame -- if true, don't add an undo that is similar to the last
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if not isinstance(nodes, list):
            nodes = [nodes]
        if (skipSame and listRef and isinstance(listRef[-1], ChildListUndo)
            and len(listRef[-1].dataList) == 1 and len(nodes) == 1 and
            nodes[0] == listRef[-1].dataList[0][0]):
            return
        self.addBranch = addBranch
        self.treeFormats = None
        if treeFormats:
            self.treeFormats = copy.deepcopy(treeFormats)
        for node in nodes:
            if addBranch:
                for child in node.descendantGen():
                    self.dataList.append((child, child.childList[:]))
            else:
                self.dataList.append((node, node.childList[:]))
                if addChildren:
                    for child in node.childList:
                        self.dataList.append((child, child.childList[:]))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            formats = None
            if self.treeFormats:
                formats = self.treeStructRef.treeFormats
            ChildListUndo(redoRef, [data[0] for data in self.dataList], False,
                          False, formats, False, False)
        if self.treeFormats:
            self.treeStructRef.configDialogFormats = self.treeFormats
            self.treeStructRef.applyConfigDialogFormats(False)
            globalref.mainControl.updateConfigDialog()
        newNodes = set()
        oldNodeFreq = dict()
        for node, childList in self.dataList:
            origChildren = set(node.childList)
            children = set(childList)
            newNodes = newNodes | (children - origChildren)
            for oldNode in (origChildren - children):
                for child in oldNode.descendantGen():
                    oldNodeFreq[child] = oldNodeFreq.get(child, 0) + 1
        for node, childList in self.dataList:
            node.childList = childList
        for newNode in newNodes:
            for child in newNode.descendantGen():
                self.treeStructRef.addNodeDictRef(child)
        for oldNode, freq in oldNodeFreq.items():
            if oldNode not in newNodes and freq >= len(oldNode.spotRefs):
                self.treeStructRef.removeNodeDictRef(oldNode)
            oldNode.removeInvalidSpotRefs()
        for node, childList in self.dataList:
            for child in childList:
                if child in newNodes:
                    child.addSpotRef(node)


class ChildDataUndo(UndoBase):
    """Info for undo/redo of tree node child data and lists.
    """
    def __init__(self, listRef, nodes, addBranch=False, treeFormats=None,
                 notRedo=True):
        """Create the child data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a parent node or a list of parents to save children
            addBranch -- if True, include all branch nodes
            treeFormats -- the format data to store
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if not isinstance(nodes, list):
            nodes = [nodes]
        self.addBranch = addBranch
        self.treeFormats = None
        if treeFormats:
            self.treeFormats = copy.deepcopy(treeFormats)
        for parent in nodes:
            if addBranch:
                for node in parent.descendantGen():
                    self.dataList.append((node, node.data.copy(),
                                          node.childList[:]))
            else:
                self.dataList.append((parent, parent.data.copy(),
                                      parent.childList[:]))
                for node in parent.childList:
                    self.dataList.append((node, node.data.copy(),
                                          node.childList[:]))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            formats = None
            if self.treeFormats:
                formats = self.treeStructRef.treeFormats
            ChildDataUndo(redoRef, [data[0] for data in self.dataList], False,
                          formats, False)
        if self.treeFormats:
            self.treeStructRef.configDialogFormats = self.treeFormats
            self.treeStructRef.applyConfigDialogFormats(False)
            globalref.mainControl.updateConfigDialog()
        newNodes = set()
        oldNodeFreq = dict()
        for node, data, childList in self.dataList:
            origChildren = set(node.childList)
            children = set(childList)
            newNodes = newNodes | (children - origChildren)
            for oldNode in (origChildren - children):
                for child in oldNode.descendantGen():
                    oldNodeFreq[child] = oldNodeFreq.get(child, 0) + 1
        for node, data, childList in self.dataList:
            node.childList = childList
            node.data = data
        for newNode in newNodes.copy():
            for child in newNode.descendantGen():
                self.treeStructRef.addNodeDictRef(child)
                newNodes.add(child)
        for oldNode, freq in oldNodeFreq.items():
            if oldNode not in newNodes and freq >= len(oldNode.spotRefs):
                self.treeStructRef.removeNodeDictRef(oldNode)
            oldNode.removeInvalidSpotRefs()
        for node, data, childList in self.dataList:
            for child in childList:
                if child in newNodes:
                    child.addSpotRef(node, not self.addBranch)


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
        if not isinstance(nodes, list):
            nodes = [nodes]
        for node in nodes:
            self.dataList.append((node, node.formatRef.name, node.data.copy()))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            TypeUndo(redoRef, [data[0] for data in self.dataList], False)
        for node, formatName, data in self.dataList:
            node.formatRef = self.treeStructRef.treeFormats[formatName]
            node.data = data


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
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            FormatUndo(redoRef, self.treeStructRef.treeFormats,
                       self.treeFormats, False)
        self.treeStructRef.configDialogFormats = self.treeFormats
        self.treeStructRef.applyConfigDialogFormats(False)
        globalref.mainControl.updateConfigDialog()


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
