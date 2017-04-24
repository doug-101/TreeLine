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
        item = self.pop()
        item.undo(self.altListRef)
        selectSpots = [node.spotByNumber(num, self.localControlRef.model) for
                       (node, num) in item.selectedTuples]
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
        self.selectedSpots = (localControlRef.currentSelectionModel().
                              selectedSpots())
        self.selectedTuples = [(spot.nodeRef, spot.instanceNumber())
                               for spot in
                               localControlRef.currentSelectionModel().
                               selectedSpots()]
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
            self.dataList.append((node, node.data.copy(), fieldRef))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            DataUndo(redoRef, [data[0] for data in self.dataList],
                     False, '', False)
        for node, data, fieldRef in self.dataList:
            node.data = data


class ChildListUndo(UndoBase):
    """Info for undo/redo of tree node child lists.
    """
    def __init__(self, listRef, nodes, skipSame=False, notRedo=True):
        """Create the child list undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a parent node or a list of parents to save children
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
            for child in node.childList:
                if child not in childList:
                    for oldNode in child.descendantGen():
                        if len(oldNode.parents()) <= 1:
                            self.treeStructRef.removeNodeDictRef(oldNode)
                        else:
                            oldNode.removeInvalidSpotRefs(False)
            origChildList = node.childList
            node.childList = childList
            for child in childList:
                if child not in origChildList:
                    child.addSpotRef(node)
                    for newChild in child.descendantGen():
                        self.treeStructRef.addNodeDictRef(newChild)


class ChildDataUndo(UndoBase):
    """Info for undo/redo of tree node child data and lists.
    """
    def __init__(self, listRef, nodes, notRedo=True):
        """Create the child data undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a parent node or a list of parents to save children
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if not isinstance(nodes, list):
            nodes = [nodes]
        for parent in nodes:
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
            ChildDataUndo(redoRef, [data[0] for data in self.dataList], False)
        for node, data, childList in self.dataList:
            for child in node.childList:
                if child not in childList:
                    for oldNode in child.descendantGen():
                        if len(oldNode.parents()) <= 1:
                            self.treeStructRef.removeNodeDictRef(oldNode)
                        else:
                            oldNode.removeInvalidSpotRefs(False)
            node.data = data
            origChildList = node.childList
            node.childList = childList
            for child in childList:
                if child not in origChildList:
                    child.addSpotRef(node)
                    for newChild in child.descendantGen():
                        self.treeStructRef.addNodeDictRef(newChild)


class BranchUndo(UndoBase):
    """Info for undo/redo of full tree branches.

    Includes all node data and child lists.
    """
    def __init__(self, listRef, nodes, notRedo=True):
        """Create the branch undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a node or a list of nodes to save children
            notRedo -- if True, add clones and clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        if not isinstance(nodes, list):
            nodes = [nodes]
        for parent in nodes:
            for node in parent.descendantGen():
                self.dataList.append((node, node.data.copy(),
                                      node.childList[:]))
        listRef.addUndoObj(self, notRedo)

    def undo(self, redoRef):
        """Save current state to redoRef and restore saved state.

        Arguments:
            redoRef -- the redo list where the current state is saved
        """
        if redoRef != None:
            BranchUndo(redoRef, [data[0] for data in self.dataList], False)
        for node, data, childList in self.dataList:
            for child in node.childList:
                if child not in childList:
                    for oldNode in child.descendantGen():
                        if len(oldNode.parents()) <= 1:
                            self.treeStructRef.removeNodeDictRef(oldNode)
                        else:
                            oldNode.removeInvalidSpotRefs(False)
            node.data = data
            origChildList = node.childList
            node.childList = childList
            for child in childList:
                if child not in origChildList:
                    child.addSpotRef(node)
                    self.treeStructRef.addNodeDictRef(child)


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
        dialog = globalref.mainControl.configDialog
        if dialog and dialog.isVisible():
            dialog.reset()


class ChildListFormatUndo(UndoBase):
    """Info for undo/redo of tree node child lists and type format changes.
    """
    def __init__(self, listRef, nodes, treeFormats, notRedo=True):
        """Create the child list undo class and add it to the undoStore.

        Arguments:
            listRef -- a ref to the undo/redo list this gets added to
            nodes -- a parent node or a list of parents to save children
            treeFormats -- the format data to store
            notRedo -- if True, clear redo list (after changes)
        """
        super().__init__(listRef.localControlRef)
        self.treeFormats = copy.deepcopy(treeFormats)
        if not isinstance(nodes, list):
            nodes = [nodes]
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
                          self.treeStructRef.treeFormats, False)
        self.treeStructRef.configDialogFormats = self.treeFormats
        self.treeStructRef.applyConfigDialogFormats(False)
        dialog = globalref.mainControl.configDialog
        if dialog and dialog.isVisible():
            dialog.reset()
        for node, childList in self.dataList:
            for child in node.childList:
                if child not in childList:
                    for oldNode in child.descendantGen():
                        if len(oldNode.parents()) <= 1:
                            self.treeStructRef.removeNodeDictRef(oldNode)
                        else:
                            oldNode.removeInvalidSpotRefs(False)
            origChildList = node.childList
            node.childList = childList
            for child in childList:
                if child not in origChildList:
                    child.addSpotRef(node)
                    for newChild in child.descendantGen():
                        self.treeStructRef.addNodeDictRef(newChild)
