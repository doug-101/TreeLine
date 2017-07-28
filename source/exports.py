#!/usr/bin/env python3

#******************************************************************************
# exports.py, provides classes for a file export dialog and export functions
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import os
import pathlib
import re
import copy
import io
import zipfile
import csv
from xml.etree import ElementTree
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontInfo
from PyQt5.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QDialog,
                             QFileDialog, QGroupBox, QHBoxLayout, QLabel,
                             QRadioButton, QSpinBox, QVBoxLayout, QWizard,
                             QWizardPage)
import treestructure
import treenode
import treeformats
import nodeformat
import treeoutput
import globalref
try:
    from __main__ import __version__
except ImportError:
    __version__ = ''

_bookmarkTitle = _('Bookmarks')
_odfNamespace = {'fo':
                 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
                 'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
                 'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
                 'svg':
                 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
                 'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
                 'manifest':
                 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'}

class ExportControl:
    """Control to do file exports for tree branches and nodes.
    """
    def __init__(self, structure, selectedNodes, defaultPathObj, printData):
        """Initialize export control object.

        Arguments:
            structure -- the tree structure ref for exporting the entire tree
            selectedNodes -- the selection for exporting partial trees
            defaultPathObj -- path object to use as file dialog default
            printData -- a ref to print data for old treeline exports
        """
        self.structure = structure
        self.selectedNodes = selectedNodes
        self.defaultPathObj = defaultPathObj
        self.printData = printData

    def interactiveExport(self):
        """Prompt the user for types, options, filename & proceed with export.

        Return True if export is successful.
        """
        exportMethods = {'htmlSingle': self.exportHtmlSingle,
                         'htmlNavSingle': self.exportHtmlNavSingle,
                         'htmlPages': self.exportHtmlPages,
                         'htmlTables': self.exportHtmlTables,
                         'textTitles': self.exportTextTitles,
                         'textPlain': self.exportTextPlain,
                         'textTableCsv': self.exportTextTableCsv,
                         'textTableTab': self.exportTextTableTab,
                         'oldTreeLine': self.exportOldTreeLine,
                         'treeLineSubtree': self.exportSubtree,
                         'xmlGeneric': self.exportXmlGeneric,
                         'odfText': self.exportOdfText,
                         'bookmarksHtml': self.exportBookmarksHtml,
                         'bookmarksXbel': self.exportBookmarksXbel}
        exportDialog = ExportDialog(len(self.selectedNodes),
                                    QApplication.activeWindow())
        if exportDialog.exec_() == QDialog.Accepted:
            result = exportMethods[ExportDialog.currentSubtype]()
            QApplication.restoreOverrideCursor()
            return result
        return False

    def getFileName(self, dialogTitle, defaultExt='txt'):
        """Prompt the user for a filename and return a path object.

        Arguments:
            dialogTitle -- the title for use on the dialog window
            defaultExt -- the default file extension from globalref
        """
        filters = ';;'.join((globalref.fileFilters[defaultExt],
                             globalref.fileFilters['all']))
        if self.defaultPathObj.name:
            self.defaultPathObj = self.defaultPathObj.with_suffix('.' +
                                                                  defaultExt)
        filePath, selectFilter = QFileDialog.getSaveFileName(QApplication.
                                                      activeWindow(),
                                                      dialogTitle,
                                                      str(self.defaultPathObj),
                                                      filters)
        if filePath:
            pathObj = pathlib.Path(filePath)
            if not pathObj.suffix:
                pathObj = pathObj.with_suffix('.' + defaultExt)
            return pathObj
        return None


    def exportHtmlSingle(self, pathObj=None):
        """Export to a single web page, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export HTML'), 'html')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        outputGroup = treeoutput.OutputGroup(self.selectedNodes,
                                             ExportDialog.includeRoot,
                                             ExportDialog.exportWhat !=
                                             ExportDialog.selectNode,
                                             ExportDialog.openOnly, True)
        outputGroup.addBlanksBetween()
        outputGroup.addIndents()
        outputGroup.addSiblingPrefixes()
        outGroups = outputGroup.splitColumns(ExportDialog.numColumns)
        htmlTitle = pathObj.stem
        indent = globalref.genOptions.getValue('IndentOffset')
        lines = ['<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 '
                 'Transitional//EN">', '<html>', '<head>',
                 '<meta http-equiv="Content-Type" content="text/html; '
                 'charset=utf-8">', '<title>{0}</title>'.format(htmlTitle),
                 '<style type="text/css"><!--',
                 'div {{margin-left: {0}em}}'.format(indent),
                 'td {padding: 10px}', 'tr {vertical-align: top}',
                 '--></style>', '</head>', '<body>']
        if ExportDialog.addHeader:
            headerText = (globalref.mainControl.activeControl.printData.
                          formatHeaderFooter(True))
            if headerText:
                lines.append(headerText)
        lines.extend(['<table>', '<tr><td>'])
        lines.extend(outGroups[0].getLines())
        for group in outGroups[1:]:
            lines.append('</td><td>')
            lines.extend(group.getLines())
        lines.extend(['</td></tr>', '</table>'])
        if ExportDialog.addHeader:
            footerText = (globalref.mainControl.activeControl.printData.
                          formatHeaderFooter(False))
            if footerText:
                lines.append(footerText)
        lines.extend(['</body>', '</html>'])
        with pathObj.open('w', encoding='utf-8') as f:
            f.writelines([(line + '\n') for line in lines])
        return True

    def exportHtmlNavSingle(self, pathObj=None):
        """Export single web page with a navigation pane, ExportDialog options.
        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export HTML'), 'html')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        outputGroup = treeoutput.OutputGroup(self.selectedNodes,
                                             ExportDialog.includeRoot, True,
                                             ExportDialog.openOnly, True,
                                             ExportDialog.navPaneLevels)
        outputGroup.addBlanksBetween()
        outputGroup.addIndents()
        outputGroup.addSiblingPrefixes()
        htmlTitle = pathObj.stem
        indent = globalref.genOptions.getValue('IndentOffset')
        lines = ['<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 '
                 'Transitional//EN">', '<html>', '<head>',
                 '<meta http-equiv="Content-Type" content="text/html; '
                 'charset=utf-8">', '<title>{0}</title>'.format(htmlTitle),
                 '<style type="text/css"><!--',
                 '   #sidebar {',
                 '      width: 16em;',
                 '      float: left;',
                 '      border-right: 1px solid black;',
                 '   }',
                 '   #sidebar div {{margin-left: {0}em;}}'.format(indent),
                 '   #content {',
                 '      margin-left: 16em;',
                 '      border-left: 1px solid black;',
                 '      padding-left: 6px;',
                 '   }',
                 '   #content div {{margin-left: {0}em;}}'.format(indent),
                 '--></style>',
                 '</head>', '<body>', '<div id="sidebar">']
        prevLevel = 0
        for parent in self.selectedNodes:
            for node, level in parent.levelDescendantGen(ExportDialog.
                                                         includeRoot,
                                                         ExportDialog.
                                                         navPaneLevels,
                                                         ExportDialog.
                                                         openOnly):
                if level > prevLevel:
                    lines.append('<div>')
                while level < prevLevel:
                    lines.append('</div>')
                    prevLevel -= 1
                lines.append('&bull; <a href="#{0}">{1}</a><br />'.
                             format(node.uniqueId, node.title()))
                prevLevel = level
        while level > 0:
            lines.append('</div>')
            level -= 1
        lines.extend(['</div>', '<div id="content">'])
        if ExportDialog.addHeader:
            headerText = (globalref.mainControl.activeControl.printData.
                          formatHeaderFooter(True))
            if headerText:
                lines.append(headerText)
        lines.extend(outputGroup.getLines())
        if ExportDialog.addHeader:
            footerText = (globalref.mainControl.activeControl.printData.
                          formatHeaderFooter(False))
            if footerText:
                lines.append(footerText)
        lines.extend(['</div>', '</body>', '</html>'])
        with pathObj.open('w', encoding='utf-8') as f:
            f.writelines([(line + '\n') for line in lines])
        return True


    def exportHtmlPages(self, pathObj=None):
        """Export multiple web pages with navigation, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            path = QFileDialog.getExistingDirectory(QApplication.
                                                   activeWindow(),
                                                   _('TreeLine - Export HTML'),
                                                   str(self.defaultPathObj))
            if not path:
                return False
            pathObj = pathlib.Path(path)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        oldDir = os.getcwd()
        os.chdir(str(pathObj))
        indent = globalref.genOptions.getValue('IndentOffset')
        cssLines = ['#sidebar {',
                    '   width: 16em;',
                    '   float: left;',
                    '   border-right: 1px solid black;',
                    '}',
                    '#sidebar div {{margin-left: {0}em;}}'.format(indent),
                    '#content {',
                    '   margin-left: 16em;',
                    '   border-left: 1px solid black;',
                    '   padding-left: 6px;',
                    '}']
        with open('default.css', 'w', encoding='utf-8') as f:
            f.writelines([(line + '\n') for line in cssLines])
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        if len(self.selectedNodes) > 1:
            modelRef = self.selectedNodes[0].modelRef
            dummyFormat = modelRef.formats.addDummyRootType()
            root = treenode.TreeNode(None, dummyFormat.name, modelRef)
            name = self.defaultPathObj.stem
            if not name:
                name = treemodel.defaultRootName
            root.setTitle(name)
            for node in self.selectedNodes:
                root.childList.append(copy.copy(node))
                root.childList[-1].parent = root
        else:
            root = self.selectedNodes[0]
        root.exportHtmlPage()
        root.modelRef.formats.removeDummyRootType()
        os.chdir(oldDir)
        return True

    def exportHtmlTables(self, pathObj=None):
        """Export to multiple web page tables, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            path = QFileDialog.getExistingDirectory(QApplication.
                                                   activeWindow(),
                                                   _('TreeLine - Export HTML'),
                                                   str(self.defaultPathObj))
            if not path:
                return False
            pathObj = pathlib.Path(path)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        oldDir = os.getcwd()
        os.chdir(str(pathObj))
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        if len(self.selectedNodes) > 1:
            modelRef = self.selectedNodes[0].modelRef
            dummyFormat = modelRef.formats.addDummyRootType()
            root = treenode.TreeNode(None, dummyFormat.name, modelRef)
            name = self.defaultPathObj.stem
            if not name:
                name = treemodel.defaultRootName
            root.setTitle(name)
            for node in self.selectedNodes:
                root.childList.append(copy.copy(node))
                root.childList[-1].parent = root
        else:
            root = self.selectedNodes[0]
        root.exportHtmlTable()
        root.modelRef.formats.removeDummyRootType()
        os.chdir(oldDir)
        return False

    def exportTextTitles(self, pathObj=None):
        """Export tabbed title text, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export Text Titles'),
                                       'txt')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        if ExportDialog.exportWhat == ExportDialog.selectNode:
            lines = [node.title() for node in self.selectedNodes]
        else:
            lines = []
            initLevel = 0 if ExportDialog.includeRoot else -1
            for node in self.selectedNodes:
                text = node.exportTitleText(initLevel, ExportDialog.openOnly)
                if not ExportDialog.includeRoot:
                    del text[0]
                lines.extend(text)
        with pathObj.open('w', encoding=globalref.localTextEncoding) as f:
            f.writelines([(line + '\n') for line in lines])
        return True

    def exportTextPlain(self, pathObj=None):
        """Export unformatted text for all output, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export Plain Text'),
                                       'txt')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        lines = []
        for root in self.selectedNodes:
            if ExportDialog.includeRoot:
                lines.extend(root.formatOutput(True))
                if root.nodeFormat().spaceBetween:
                    lines.append('')
            if not ExportDialog.exportWhat == ExportDialog.selectNode:
                for node in  (root.
                              selectiveDescendantGen(ExportDialog.openOnly)):
                    lines.extend(node.formatOutput(True))
                    if node.nodeFormat().spaceBetween:
                        lines.append('')
        with pathObj.open('w', encoding=globalref.localTextEncoding) as f:
            f.writelines([(line + '\n') for line in lines])
        return True

    def exportTextTableCsv(self, pathObj=None):
        """Export child CSV delimited text table, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export Text Tables'),
                                       'csv')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.selectNode:
            nodeList = self.selectedNodes
        else:
            nodeList = []
            for node in self.selectedNodes:
                nodeList.extend(node.childList)
        typeList = []
        headings = []
        for node in nodeList:
            nodeFormat = node.nodeFormat()
            if nodeFormat not in typeList:
                for fieldName in nodeFormat.fieldNames():
                    if fieldName not in headings:
                        headings.append(fieldName)
                typeList.append(nodeFormat)
        lines = [headings]
        for node in nodeList:
            lines.append([node.data.get(head, '') for head in headings])
        with pathObj.open('w', newline='',
                          encoding=globalref.localTextEncoding) as f:
            writer = csv.writer(f)
            writer.writerows(lines)
        return True

    def exportTextTableTab(self, pathObj=None):
        """Export child tab delimited text table, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export Text Tables'),
                                       'txt')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.selectNode:
            nodeList = self.selectedNodes
        else:
            nodeList = []
            for node in self.selectedNodes:
                nodeList.extend(node.childList)
        typeList = []
        headings = []
        for node in nodeList:
            nodeFormat = node.nodeFormat()
            if nodeFormat not in typeList:
                for fieldName in nodeFormat.fieldNames():
                    if fieldName not in headings:
                        headings.append(fieldName)
                typeList.append(nodeFormat)
        lines = ['\t'.join(headings)]
        for node in nodeList:
            lines.append('\t'.join([node.data.get(head, '') for head in
                                    headings]))
        with pathObj.open('w', encoding=globalref.localTextEncoding) as f:
            f.writelines([(line + '\n') for line in lines])
        return True

    def exportOldTreeLine(self, pathObj=None):
        """Export old TreeLine version (2.0.x), use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export TreeLine Subtree'),
                                       'trl')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if not ExportDialog.exportWhat == ExportDialog.entireTree:
            self.structure = treestructure.TreeStructure(topNodes=self.
                                                         selectedNodes,
                                                         addSpots=False)
        if len(self.structure.childList) > 1:
            rootType = nodeformat.NodeFormat(treeformats.defaultTypeName,
                                             self.structure.treeFormats,
                                             addDefaultField=True)
            self.structure.treeFormats.addTypeIfMissing(rootType)
            root = treenode.TreeNode(self.structure.
                                     treeFormats[treeformats.defaultTypeName])
            root.setTitle(treestructure.defaultRootTitle)
            self.structure.addNodeDictRef(root)
            root.childList = self.structure.childList
            self.structure.childList = [root]
        addBranches = ExportDialog.exportWhat != ExportDialog.selectNode
        idDict = {}
        for node in self.structure.childList[0].descendantGen():
            _setOldUniqueId(idDict, node)
        idDict = {i[1]: i[0] for i in idDict.items()}  # reverse (new id keys)
        rootElement = _oldElementXml(self.structure.childList[0],
                                     self.structure, idDict)
        if __version__:
            rootElement.set('tlversion', __version__)
        rootElement.attrib.update(_convertOldPrintData(self.printData.
                                                       fileData()))
        elementTree = ElementTree.ElementTree(rootElement)
        elementTree.write(str(pathObj), 'utf-8', True)
        return True

    def exportSubtree(self, pathObj=None):
        """Export TreeLine subtree, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export TreeLine Subtree'),
                                       'trln')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        addBranches = ExportDialog.exportWhat != ExportDialog.selectNode
        if len(self.selectedNodes) > 1:
            modelRef = self.selectedNodes[0].modelRef
            dummyFormat = modelRef.formats.addDummyRootType()
            root = treenode.TreeNode(None, dummyFormat.name, modelRef)
            name = self.defaultPathObj.stem
            if not name:
                name = treemodel.defaultRootName
            root.setTitle(name)
            for node in self.selectedNodes:
                root.childList.append(copy.copy(node))
                root.childList[-1].parent = root
        else:
            root = self.selectedNodes[0]
        rootElement = root.elementXml(addChildren=addBranches)
        rootElement.attrib.update(globalref.mainControl.activeControl.
                                  printData.xmlAttr())
        elementTree = ElementTree.ElementTree(rootElement)
        elementTree.write(str(pathObj), 'utf-8', True)
        root.modelRef.formats.removeDummyRootType()
        return True

    def exportXmlGeneric(self, pathObj=None):
        """Export generic XML, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export Generic XML'),
                                       'xml')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        addBranches = ExportDialog.exportWhat != ExportDialog.selectNode
        if len(self.selectedNodes) > 1:
            rootElement = ElementTree.Element(treeformat.defaultTypeName)
            for node in self.selectedNodes:
                rootElement.append(node.exportGenericXml(addBranches))
        else:
            rootElement = self.selectedNodes[0].exportGenericXml(addBranches)
        elementTree = ElementTree.ElementTree(rootElement)
        elementTree.write(str(pathObj),  'utf-8', True)
        return True

    def exportOdfText(self, pathObj=None):
        """Export an ODF text file, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export ODF Text'), 'odt')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        addBranches = ExportDialog.exportWhat != ExportDialog.selectNode
        for prefix, uri in _odfNamespace.items():
            ElementTree.register_namespace(prefix, uri)

        versionAttr = {'office:version': '1.0'}
        fontInfo = QFontInfo(globalref.mainControl.activeControl.
                                   activeWindow.editorSplitter.widget(0).
                                   font())
        fontAttr = {'style:font-pitch':
                    'fixed' if fontInfo.fixedPitch() else 'variable',
                    'style:name': fontInfo.family(),
                    'svg:font-family': fontInfo.family()}
        fontElem = _addOdfElement('office:font-face-decls')
        _addOdfElement('style:font-face', fontElem, fontAttr)
        fontSizeDelta = 2

        contentRoot = _addOdfElement('office:document-content',
                                     attr=versionAttr)
        contentRoot.append(fontElem)
        contentBodyElem = _addOdfElement('office:body', contentRoot)
        contentTextElem = _addOdfElement('office:text', contentBodyElem)
        maxLevel = 0
        for node in self.selectedNodes:
            level = node.exportOdf(contentTextElem, addBranches)
            maxLevel = max(level, maxLevel)

        manifestRoot = _addOdfElement('manifest:manifest')
        _addOdfElement('manifest:file-entry', manifestRoot,
                       {'manifest:media-type':
                        'application/vnd.oasis.opendocument.text',
                        'manifest:full-path': '/'})
        _addOdfElement('manifest:file-entry', manifestRoot,
                       {'manifest:media-type': 'text/xml',
                        'manifest:full-path': 'content.xml'})
        _addOdfElement('manifest:file-entry', manifestRoot,
                       {'manifest:media-type': 'text/xml',
                        'manifest:full-path': 'styles.xml'})

        styleRoot = _addOdfElement('office:document-styles', attr=versionAttr)
        styleRoot.append(fontElem)
        stylesElem = _addOdfElement('office:styles', styleRoot)
        defaultStyleElem = _addOdfElement('style:default-style', stylesElem,
                                          {'style:family': 'paragraph'})
        _addOdfElement('style:paragraph-properties', defaultStyleElem,
                       {'style:writing-mode': 'page'})
        _addOdfElement('style:text-properties', defaultStyleElem,
                       {'fo:font-size': '{0}pt'.format(fontInfo.pointSize()),
                        'fo:hyphenate': 'false',
                        'style:font-name': fontInfo.family()})
        _addOdfElement('style:style', stylesElem,
                       {'style:name': 'Standard', 'style:class': 'text',
                        'style:family': 'paragraph'})
        bodyStyleElem = _addOdfElement('style:style', stylesElem,
                                      {'style:name': 'Text_20_body',
                                       'style:display-name': 'Text body',
                                       'style:class': 'text',
                                       'style:family': 'paragraph',
                                       'style:parent-style-name': 'Standard'})
        _addOdfElement('style:paragraph-properties', bodyStyleElem,
                       {'fo:margin-bottom': '6.0pt'})
        headStyleElem =  _addOdfElement('style:style', stylesElem,
                                       {'style:name': 'Heading',
                                        'style:class': 'text',
                                        'style:family': 'paragraph',
                                        'style:next-style-name':
                                        'Text_20_body',
                                        'style:parent-style-name': 'Standard'})
        _addOdfElement('style:paragraph-properties', headStyleElem,
                       {'fo:keep-with-next': 'always',
                        'fo:margin-bottom': '6.0pt',
                        'fo:margin-top': '12.0pt'})
        _addOdfElement('style:text-properties', headStyleElem,
                       {'fo:font-size':
                        '{0}pt'.format(fontInfo.pointSize() + fontSizeDelta),
                        'style:font-name': fontInfo.family()})
        outlineStyleElem = _addOdfElement('text:outline-style')
        for level in range(1, maxLevel + 1):
            size = fontInfo.pointSize()
            if level <= 2:
                size += 2 * fontSizeDelta
            elif level <= 4:
                size += fontSizeDelta
            levelStyleElem = _addOdfElement('style:style', stylesElem,
                                            {'style:name':
                                             'Heading_20_{0}'.format(level),
                                             'style:display-name':
                                             'Heading {0}'.format(level),
                                             'style:class': 'text',
                                             'style:family': 'paragraph',
                                             'style:parent-style-name':
                                             'Heading',
                                             'style:default-outline-level':
                                             '{0}'.format(level)})
            levelTextElem = _addOdfElement('style:text-properties',
                                           levelStyleElem,
                                           {'fo:font-size':
                                            '{0}pt'.format(size),
                                            'fo:font-weight': 'bold'})
            if level % 2 == 0:
                levelTextElem.set('fo:font-style', 'italic')
            _addOdfElement('text:outline-level-style', outlineStyleElem,
                           {'text:level': '{0}'.format(level),
                            'style:num-format': ''})
        stylesElem.append(outlineStyleElem)
        autoStyleElem = _addOdfElement('office:automatic-styles', styleRoot)
        pageLayElem = _addOdfElement('style:page-layout', autoStyleElem,
                                     {'style:name': 'pm1'})
        _addOdfElement('style:page-layout-properties', pageLayElem,
                       {'fo:margin-bottom': '0.75in',
                        'fo:margin-left': '0.75in',
                        'fo:margin-right': '0.75in', 'fo:margin-top': '0.75in',
                        'fo:page-height': '11in', 'fo:page-width': '8.5in',
                        'style:print-orientation': 'portrait'})
        masterStyleElem = _addOdfElement('office:master-styles', styleRoot)
        _addOdfElement('style:master-page', masterStyleElem,
                       {'style:name': 'Standard',
                        'style:page-layout-name': 'pm1'})

        with zipfile.ZipFile(str(pathObj), 'w',
                             zipfile.ZIP_DEFLATED) as odfZip:
            _addElemToZip(odfZip, contentRoot, 'content.xml')
            _addElemToZip(odfZip, manifestRoot, 'META-INF/manifest.xml')
            _addElemToZip(odfZip, styleRoot, 'styles.xml')
        return True

    def exportBookmarksHtml(self, pathObj=None):
        """Export HTML format bookmarks, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export HTML Bookmarks'),
                                       'html')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        addBranches = ExportDialog.exportWhat != ExportDialog.selectNode
        title = _bookmarkTitle
        if len(self.selectedNodes) == 1 and addBranches:
            title = self.selectedNodes[0].title()
            self.selectedNodes = self.selectedNodes[0].childList
        lines = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>',
                 '<meta http-equiv="Content-Type" content="text/html; '
                 'charset=utf-8">', '<title>{0}</title>'.format(title),
                 '<h1>{0}</h1>'.format(title)]
        for node in self.selectedNodes:
            lines.extend(node.exportHtmlBookmarks(addBranches))
        with pathObj.open('w', encoding='utf-8') as f:
            f.writelines([(line + '\n') for line in lines])
        return True

    def exportBookmarksXbel(self, pathObj=None):
        """Export XBEL format bookmarks, use ExportDialog options.

        Prompt user for path if not given in argument.
        Return True on successful export.
        Arguments:
            pathObj -- use if given, otherwise prompt user
        """
        if not pathObj:
            pathObj = self.getFileName(_('TreeLine - Export XBEL Bookmarks'),
                                       'xml')
            if not pathObj:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if ExportDialog.exportWhat == ExportDialog.entireTree:
            self.selectedNodes = self.structure.childList
        addBranches = ExportDialog.exportWhat != ExportDialog.selectNode
        title = _bookmarkTitle
        if len(self.selectedNodes) == 1 and addBranches:
            title = self.selectedNodes[0].title()
            self.selectedNodes = self.selectedNodes[0].childList
        rootElem = ElementTree.Element('xbel')
        titleElem = ElementTree.Element('title')
        titleElem.text = title
        rootElem.append(titleElem)
        for node in self.selectedNodes:
            rootElem.append(node.exportXbel(addBranches))
        elementTree = ElementTree.ElementTree(rootElem)
        with pathObj.open('wb') as f:
            f.write(b'<!DOCTYPE xbel>\n')
            elementTree.write(f, 'utf-8', False)
        return True


_linkRe = re.compile(r'<a [^>]*href="#(.*?)"[^>]*>.*?</a>', re.I | re.S)

def _oldElementXml(node, structRef, idDict, skipTypeFormats=None,
                   extraFormats=True, addChildren=True):
    """Return an Element object with the XML for this node's branch.

    Arguments:
        node -- the root node to save
        structRef -- a ref to the tree structure
        idDict -- a dict of new IDs to old IDs
        skipTypeFormats -- a set of node format types not included in XML
        extraFormats -- if True, includes unused format info
        addChildren -- if True, include descendant data
    """
    if skipTypeFormats == None:
        skipTypeFormats = set()
    nodeFormat = node.formatRef
    addFormat = nodeFormat.name not in skipTypeFormats
    element = ElementTree.Element(nodeFormat.name, {'item':'y'})
    # add line feeds to make output somewhat readable
    element.tail = '\n'
    element.text = '\n'
    element.set('uniqueid', idDict[node.uId])
    if addFormat:
        element.attrib.update(_convertOldNodeFormat(nodeFormat.storeFormat()))
        skipTypeFormats.add(nodeFormat.name)
    firstField = True
    for field in nodeFormat.fields():
        text = node.data.get(field.name, '')
        if text or addFormat:
            fieldElement = ElementTree.SubElement(element, field.name)
            fieldElement.tail = '\n'
            if field.typeName in ('Date', 'DateTime'):
                text = text.replace('-', '/')
            if (field.typeName in ('Time', 'DateTime') and
                text.endswith('.000000')):
                text = text[:-7]
            linkCount = 0
            startPos = 0
            while True:
                match = _linkRe.search(text, startPos)
                if not match:
                    break
                uId = idDict.get(match.group(1), '')
                if uId:
                    text = text[:match.start(1)] + uId + text[match.end(1):]
                    linkCount += 1
                startPos = match.start(1)
            if linkCount:
                fieldElement.attrib['linkcount'] = repr(linkCount)
            fieldElement.text = text
            if addFormat:
                fieldElement.attrib.update(_convertOldFieldFormat(field.
                                                                 formatData()))
                if firstField:
                    fieldElement.attrib['idref'] = 'y'
        firstField = False
    if addChildren:
        for child in node.childList:
            element.append(_oldElementXml(child, structRef, idDict,
                                          skipTypeFormats, False, True))
    nodeFormats = []
    if extraFormats:   # write format info for unused formats
        nodeFormats = list(structRef.treeFormats.values())
        if structRef.treeFormats.fileInfoFormat.fieldFormatModified:
            nodeFormats.append(structRef.treeFormats.fileInfoFormat)
    for nodeFormat in nodeFormats:
        if nodeFormat.name not in skipTypeFormats:
            formatElement = ElementTree.SubElement(element,
                                                   nodeFormat.name,
                                                   {'item':'n'})
            formatElement.tail = '\n'
            formatElement.attrib.update(_convertOldNodeFormat(nodeFormat.
                                                              storeFormat()))
            firstField = True
            for field in nodeFormat.fields():
                fieldElement = ElementTree.SubElement(formatElement,
                                                      field.name)
                fieldElement.tail = '\n'
                fieldElement.attrib.update(_convertOldFieldFormat(field.
                                                                 formatData()))
                if firstField:
                    fieldElement.attrib['idref'] = 'y'
                    firstField = False
    return element

_idReplaceCharsRe = re.compile(r'[^a-zA-Z0-9_-]+')

def _setOldUniqueId(idDict, node):
    """Set an old TreeLine unique ID for this node amd add to dict.

    Arguments:
        idDict -- a dict of old IDs to new IDs.
        node -- the node to give an old ID
    """
    nodeFormat = node.formatRef
    idField = next(iter(nodeFormat.fieldDict.values()))
    uId = idField.outputText(node, True, nodeFormat.formatHtml)
    uId = uId.strip().split('\n', 1)[0]
    maxLength = 50
    if len(uId) > maxLength:
        pos = uId.rfind(' ', maxLength // 2, maxLength + 1)
        if pos < 0:
            pos = maxLength
        uId = uId[:pos]
    uId = uId.replace(' ', '_').lower()
    uId = _idReplaceCharsRe.sub('', uId)
    if not uId:
        uId = 'id_1'
    elif not 'a' <= uId <= 'z':
        uId = 'id_' + uId
    if uId in idDict:
        if uId == 'id_1':
            uId = 'id'
        i = 1
        while uId + '_' + repr(i) in idDict:
            i += 1
        uId = uId + '_' + repr(i)
    idDict[uId] = node.uId

def _convertOldNodeFormat(attrib):
    """Return old XML node format attributes from current data.

    Arguments:
        attrib -- current node format data attributes
    """
    if 'spacebetween' in attrib and not attrib['spacebetween']:
        attrib['spacebetween'] = 'n'
    for key in ('formathtml', 'bullets', 'tables'):
        if key in attrib and attrib[key]:
            attrib[key] = 'y'
    attrib['line0'] = attrib.get('titleline', '')
    del attrib['titleline']
    for i, line in enumerate(attrib['outputlines'], 1):
        attrib['line' + repr(i)] = line
    del attrib['outputlines']
    del attrib['formatname']
    del attrib['fields']
    return attrib

def _convertOldFieldFormat(attrib):
    """Return old XML field format attributes from current data.

    Arguments:
        attrib -- current field format data attributes
    """
    if 'fieldtype' in attrib:
        attrib['type'] = attrib['fieldtype']
        del attrib['fieldtype']
    for key in ('lines', 'sortkeynum'):
        if key in attrib:
            attrib[key] = repr(attrib[key])
    if 'sortkeyfwd' in attrib and not attrib['sortkeyfwd']:
        attrib['sortkeydir'] = 'r'
    if 'evalhtml' in attrib:
        attrib['evalhtml'] = 'y' if attrib['evalhtml'] else 'n'
    if attrib['type'] in ('Date', 'Time', 'DateTime'):
        fieldFormat = attrib.get('format', '')
        if fieldFormat:
            fieldFormat = fieldFormat.replace('%A', 'dddd')
            fieldFormat = fieldFormat.replace('%a', 'ddd')
            fieldFormat = fieldFormat.replace('%d', 'dd')
            fieldFormat = fieldFormat.replace('%-d', 'd')
            fieldFormat = fieldFormat.replace('%B', 'MMMM')
            fieldFormat = fieldFormat.replace('%b', 'MMM')
            fieldFormat = fieldFormat.replace('%m', 'MM')
            fieldFormat = fieldFormat.replace('%-m', 'M')
            fieldFormat = fieldFormat.replace('%Y', 'yyyy')
            fieldFormat = fieldFormat.replace('%y', 'yy')
            fieldFormat = fieldFormat.replace('%H', 'HH')
            fieldFormat = fieldFormat.replace('%-H', 'H')
            fieldFormat = fieldFormat.replace('%I', 'hh')
            fieldFormat = fieldFormat.replace('%-I', 'h')
            fieldFormat = fieldFormat.replace('%M', 'mm')
            fieldFormat = fieldFormat.replace('%-M', 'm')
            fieldFormat = fieldFormat.replace('%S', 'ss')
            fieldFormat = fieldFormat.replace('%-S', 's')
            fieldFormat = fieldFormat.replace('%f', 'zzz')
            fieldFormat = fieldFormat.replace('%p', 'AP')
            attrib['format'] = fieldFormat
    del attrib['fieldname']
    return attrib

def _convertOldPrintData(attrib):
    """Return old XML print data attributes from current print data.

    Arguments:
        attrib -- current print data attributes
    """
    for key in ('printlines', 'printwidowcontrol', 'printportrait'):
        if key in attrib and not attrib[key]:
            attrib[key] = 'n'
    for key in ('printindentfactor', 'printpaperwidth', 'printpaperheight',
                'printheadermargin', 'printfootermargin', 'printcolumnspace',
                'printnumcolumns'):
        if key in attrib:
            attrib[key] = repr(attrib[key])
    if 'printmargins' in attrib:
        attrib['printmargins'] = ' '.join([repr(margin) for margin in
                                           attrib['printmargins']])
    return attrib


def _addElemToZip(destZip, rootElem, fileName):
    """Adds ElementTree root elements to the given zip file.

    Arguments:
        destZip -- the destination zip file
        rootElem -- the root element tree item to add
        fileName -- the file name or path in the zip file
    """
    elemTree = ElementTree.ElementTree(rootElem)
    with io.BytesIO() as output:
        elemTree.write(output, 'utf-8', True)
        destZip.writestr(fileName, output.getvalue())


def _addOdfElement(name, parent=None, attr=None):
    """Shortcut function to add elements to the ElementTree.

    Converts names and attr keys from short version (with ':') to the full URI.
    Returns the new element.
    Arguments:
        name -- the element tag
        parent -- new element is added here if given
        attr -- a dict of the element's attrbutes
    """
    if ':' in name:
        prefix, name = name.split(':', 1)
        name = '{{{0}}}{1}'.format(_odfNamespace[prefix], name)
    newAttr = {}
    if attr:
        for key, value in attr.items():
            if ':' in key:
                prefix, key = key.split(':', 1)
                key = '{{{0}}}{1}'.format(_odfNamespace[prefix], key)
            newAttr[key] = value
    elem = ElementTree.Element(name, newAttr)
    elem.tail = '\n'
    if parent is not None:
        parent.append(elem)
    return elem


class ExportDialog(QWizard):
    """Dialog/wizard for setting file export type and options.
    """
    typePage, subtypePage, optionPage = range(3)
    entireTree, selectBranch, selectNode = range(3)
    exportWhat = entireTree
    includeRoot = False
    openOnly = False
    addHeader = False
    numColumns = 1
    navPaneLevels = 2
    exportTypes = ['html', 'text', 'treeline', 'xml', 'odf', 'bookmarks']
    currentType = 'html'
    exportTypeDescript = {'html': _('&HTML'), 'text': _('&Text'),
                          'treeline': _('Tree&Line'),
                          'xml': _('&XML (generic)'), 'odf': _('&ODF Outline'),
                          'bookmarks': _('Book&marks')}
    exportSubtypes = {'html': ['htmlSingle', 'htmlNavSingle','htmlPages',
                               'htmlTables'],
                      'text': ['textTitles', 'textPlain', 'textTableCsv',
                               'textTableTab'],
                      'treeline': ['oldTreeLine', 'treeLineSubtree'],
                      'xml': ['xmlGeneric'],
                      'odf': ['odfText'],
                      'bookmarks': ['bookmarksHtml', 'bookmarksXbel']}
    currentSubtype = 'htmlSingle'
    subtypeDescript = {'htmlSingle': _('&Single HTML page'),
                       'htmlNavSingle': _('Single &HTML page with '
                                          'navigation pane'),
                       'htmlPages': _('Multiple HTML &pages with '
                                      'navigation pane'),
                       'htmlTables': _('Multiple HTML &data tables'),
                       'textTitles': _('&Tabbed title text'),
                       'textPlain': _('&Unformatted output of all text'),
                       'textTableCsv': _('&Comma delimited (CSV) table '
                                         'of children'),
                       'textTableTab': _('Tab &delimited table of children'),
                       'oldTreeLine': _('&Old TreeLine (2.0.x)'),
                       'treeLineSubtree': _('&TreeLine Subtree'),
                       'bookmarksHtml': _('&HTML format bookmarks'),
                       'bookmarksXbel': _('&XBEL format bookmarks')}
    disableEntireTree = {'textTableCsv', 'textTableTab', 'treeLineSubtree'}
    disableSelBranches = set()
    disableSelNodes = {'htmlNavSingle', 'htmlPages', 'htmlTables'}
    enableRootNode = {'htmlSingle', 'htmlNavSingle', 'textTitles',
                      'textPlain', 'ODF'}
    forceRootNodeOff = {'textTableCsv', 'textTableTab'}
    enableOpenOnly = {'htmlSingle', 'htmlNavSingle', 'textTitles',
                      'textPlain', 'ODF'}
    enableHeader = {'htmlSingle', 'htmlNavSingle', 'htmlTables'}
    enableColumns = {'htmlSingle'}
    enableNavLevels = {'htmlNavSingle'}

    def __init__(self, selectionAvail=True, parent=None):
        """Initialize the export wizard.

        Arguments:
            selectionAvail -- false if no nodes or branches are selected
            parent -- the parent window
        """
        super().__init__(parent, Qt.Dialog)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('File Export'))
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setPage(ExportDialog.typePage, ExportDialogTypePage())
        self.setPage(ExportDialog.subtypePage, ExportDialogSubtypePage())
        self.setPage(ExportDialog.optionPage,
                     ExportDialogOptionPage(selectionAvail))


class ExportDialogTypePage(QWizardPage):
    """A wizard page for selecting the main export type.
    """
    def __init__(self, parent=None):
        """Initialize the export wizard page.

        Arguments:
            parent -- parent widget, set automatically by addPage or setPage
        """
        super().__init__(parent)

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        self.setTitle(_('Choose export format type'))

        typeButtons = QButtonGroup(self)
        for id, exportType in enumerate(ExportDialog.exportTypes):
            button = QRadioButton(ExportDialog.
                                        exportTypeDescript[exportType])
            typeButtons.addButton(button, id)
            topLayout.addWidget(button)
            if exportType == ExportDialog.currentType:
                button.setChecked(True)
        typeButtons.buttonClicked[int].connect(self.setCurrentType)

    def setCurrentType(self, buttonID):
        """Set the saved current type value based on a button click.

        Also sets the subtype to a default value.
        Arguments:
            buttonId -- the ID number of the button that was clicked
        """
        ExportDialog.currentType = ExportDialog.exportTypes[buttonID]
        ExportDialog.currentSubtype = (ExportDialog.
                                   exportSubtypes[ExportDialog.currentType][0])

    def nextId(self):
        """Return the ID for the next page in the wizard sequence.
        """
        if len(ExportDialog.exportSubtypes[ExportDialog.currentType]) > 1:
            return ExportDialog.subtypePage
        return ExportDialog.optionPage


class ExportDialogSubtypePage(QWizardPage):
    """A wizard page for selecting the export subtype.
    """
    def __init__(self, parent=None):
        """Initialize the export wizard page.

        Arguments:
            parent -- parent widget, set automatically by addPage or setPage
        """
        super().__init__(parent)

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        self.setTitle(_('Choose export format subtype'))
        self.subtypeButtons = QButtonGroup(self)
        self.subtypeButtons.buttonClicked[int].connect(self.setCurrentSubtype)

    def initializePage(self):
        """Add buttons to this page based on current settings.
        """
        topLayout = self.layout()
        # remove old buttons from a previously set subtype
        for button in self.subtypeButtons.buttons():
            self.subtypeButtons.removeButton(button)
            topLayout.removeWidget(button)
            button.deleteLater()

        for id, subtype in enumerate(ExportDialog.
                                     exportSubtypes[ExportDialog.currentType]):
            button = QRadioButton(ExportDialog.subtypeDescript[subtype])
            self.subtypeButtons.addButton(button, id)
            topLayout.addWidget(button)
            if subtype == ExportDialog.currentSubtype:
                button.setChecked(True)

    def setCurrentSubtype(self, buttonId):
        """Set the saved current subtype value based on a button click.

        Arguments:
            buttonId -- the ID number of the button that was clicked
        """
        availSubtypes = ExportDialog.exportSubtypes[ExportDialog.currentType]
        ExportDialog.currentSubtype = availSubtypes[buttonId]


class ExportDialogOptionPage(QWizardPage):
    """A wizard page for selecting other export options.
    """
    def __init__(self, selectionAvail=True, parent=None):
        """Initialize the export wizard page.

        Arguments:
            selectionAvail -- false if no nodes or branches are selected
            parent -- parent widget, set automatically by addPage or setPage
        """
        super().__init__(parent)
        self.selectionAvail = selectionAvail

        topLayout = QVBoxLayout(self)
        self.setLayout(topLayout)
        self.setTitle(_('Choose export options'))

        whatGroupBox = QGroupBox(_('What to Export'))
        topLayout.addWidget(whatGroupBox)
        whatLayout = QVBoxLayout(whatGroupBox)
        self.whatButtons = QButtonGroup(self)
        treeButton = QRadioButton(_('&Entire tree'))
        self.whatButtons.addButton(treeButton, ExportDialog.entireTree)
        whatLayout.addWidget(treeButton)
        branchButton = QRadioButton(_('Selected &branches'))
        self.whatButtons.addButton(branchButton, ExportDialog.selectBranch)
        whatLayout.addWidget(branchButton)
        nodeButton = QRadioButton(_('Selected &nodes'))
        self.whatButtons.addButton(nodeButton, ExportDialog.selectNode)
        whatLayout.addWidget(nodeButton)
        self.whatButtons.button(ExportDialog.exportWhat).setChecked(True)
        self.whatButtons.buttonClicked[int].connect(self.setExportWhat)

        optionBox = QGroupBox(_('Other Options'))
        topLayout.addWidget(optionBox)
        optionLayout = QVBoxLayout(optionBox)
        self.rootButton = QCheckBox(_('&Include root node'))
        optionLayout.addWidget(self.rootButton)
        self.rootButton.setChecked(ExportDialog.includeRoot)
        self.rootButton.toggled.connect(self.setIncludeRoot)

        self.openOnlyButton = QCheckBox(_('&Only open node children'))
        optionLayout.addWidget(self.openOnlyButton)
        self.openOnlyButton.setChecked(ExportDialog.openOnly)
        self.openOnlyButton.toggled.connect(self.setOpenOnly)

        self.headerButton = QCheckBox(_('Include &print header && '
                                              'footer'))
        optionLayout.addWidget(self.headerButton)
        self.headerButton.setChecked(ExportDialog.addHeader)
        self.headerButton.toggled.connect(self.setAddHeader)

        columnLayout = QHBoxLayout()
        optionLayout.addLayout(columnLayout)
        self.numColSpin = QSpinBox()
        columnLayout.addWidget(self.numColSpin)
        self.numColSpin.setRange(1, 9)
        self.numColSpin.setMaximumWidth(40)
        self.numColSpin.setValue(ExportDialog.numColumns)
        self.colLabel = QLabel(_('&Columns'))
        columnLayout.addWidget(self.colLabel)
        self.colLabel.setBuddy(self.numColSpin)
        self.numColSpin.valueChanged.connect(self.setNumColumns)

        navLevelsLayout = QHBoxLayout()
        optionLayout.addLayout(navLevelsLayout)
        self.navLevelsSpin = QSpinBox()
        navLevelsLayout.addWidget(self.navLevelsSpin)
        self.navLevelsSpin.setRange(1, 9)
        self.navLevelsSpin.setMaximumWidth(40)
        self.navLevelsSpin.setValue(ExportDialog.navPaneLevels)
        self.navLevelsLabel = QLabel(_('Navigation pane &levels'))
        navLevelsLayout.addWidget(self.navLevelsLabel)
        self.navLevelsLabel.setBuddy(self.navLevelsSpin)
        self.navLevelsSpin.valueChanged.connect(self.setNavLevels)

    def initializePage(self):
        """Enable or disable controls based on current settings.
        """
        subtype = ExportDialog.currentSubtype
        treeButton, branchButton, nodeButton = self.whatButtons.buttons()
        treeButton.setEnabled(subtype not in ExportDialog.disableEntireTree)
        branchButton.setEnabled(subtype not in ExportDialog.disableSelBranches
                                and self.selectionAvail)
        nodeButton.setEnabled(subtype not in ExportDialog.disableSelNodes and
                              self.selectionAvail)
        num = 0
        while not self.whatButtons.checkedButton().isEnabled():
            self.whatButtons.button(num).setChecked(True)
            num += 1

        if (subtype in ExportDialog.enableRootNode and
            ExportDialog.exportWhat != ExportDialog.selectNode):
            self.rootButton.setEnabled(True)
            self.rootButton.setChecked(ExportDialog.includeRoot)
        else:
            self.rootButton.setEnabled(False)
            self.rootButton.setChecked(subtype not in
                                       ExportDialog.forceRootNodeOff)

        if (subtype in ExportDialog.enableOpenOnly and
            ExportDialog.exportWhat != ExportDialog.selectNode):
            self.openOnlyButton.setEnabled(True)
        else:
            self.openOnlyButton.setEnabled(False)
            self.openOnlyButton.setChecked(False)

        self.headerButton.setEnabled(subtype in ExportDialog.enableHeader)
        if subtype not in ExportDialog.enableHeader:
            self.headerButton.setChecked(False)

        columnsEnabled = subtype in ExportDialog.enableColumns
        self.numColSpin.setVisible(columnsEnabled)
        self.colLabel.setVisible(columnsEnabled)
        if not columnsEnabled:
            self.numColSpin.setValue(1)

        navLevelsEnabled = subtype in ExportDialog.enableNavLevels
        self.navLevelsSpin.setVisible(navLevelsEnabled)
        self.navLevelsLabel.setVisible(navLevelsEnabled)

    def setExportWhat(self, buttonNum):
        """Set what to export (all, branch, node) based on button group click.

        Arguments:
            buttonNum -- the ID number of the clicked button
        """
        ExportDialog.exportWhat = buttonNum
        self.initializePage()

    def setIncludeRoot(self, checked):
        """Set whether root node is included based on a button click.

        Arguments:
            checked -- True if the check box is checked
        """
        ExportDialog.includeRoot = checked

    def setOpenOnly(self, checked):
        """Set whether only open nodes are included based on a button click.

        Arguments:
            checked -- True if the check box is checked
        """
        ExportDialog.openOnly = checked

    def setAddHeader(self, checked):
        """Set whether headers and footers are added based on a button click.

        Arguments:
            checked -- True if the check box is checked
        """
        ExportDialog.addHeader = checked

    def setNumColumns(self, num):
        """Set number of columns based on a spin box change.

        Arguments:
            num -- the new spin box setting
        """
        ExportDialog.numColumns = num

    def setNavLevels(self, num):
        """Set number of navigation pane levels based on a spin box change.

        Arguments:
            num -- the new spin box setting
        """
        ExportDialog.navPaneLevels = num
