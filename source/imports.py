#!/usr/bin/env python3

#******************************************************************************
# imports.py, provides classes for a file import dialog and import functions
#
# TreeLine, an information storage program
# Copyright (C) 2023, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import pathlib
import re
import collections
import zipfile
import csv
import html.parser
import xml.sax.saxutils
from xml.etree import ElementTree
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
import miscdialogs
import treenode
import treestructure
import treemodel
import nodeformat
import treeformats
import urltools
import globalref


methods = collections.OrderedDict()
methods.update([(_('Text'), None),
                (_('&Tab indented text, one node per line'),
                 'importTabbedText'),
                (_('Co&mma delimited (CSV) text table with level column && '
                   'header row'), 'importTableCsvLevels'),
                (_('Comma delimited (CSV) text table &with header row'),
                 'importTableCsv'),
                (_('Tab delimited text table with header &row'),
                 'importTableTabbed'),
                (_('Plain text, one &node per line (CR delimited)'),
                 'importTextLines'),
                (_('Plain text &paragraphs (blank line delimited)'),
                 'importTextPara'),
                (_('Bookmarks'), None),
                (_('&HTML bookmarks (Mozilla Format)'), 'importMozilla'),
                (_('&XML bookmarks (XBEL format)'), 'importXbel'),
                (_('Other'), None),
                (_('Old Tree&Line File (1.x or 2.x)'), 'importOldTreeLine'),
                (_('Treepad &file (text nodes only)'), 'importTreePad'),
                (_('&Generic XML (non-TreeLine file)'), 'importXml'),
                (_('Open &Document (ODF) outline'), 'importOdfText')])
fileFilters = {'importTabbedText': 'txt',
               'importTableCsvLevels': 'csv',
               'importTableCsv': 'csv',
               'importTableTabbed': 'txt',
               'importTextLines': 'txt',
               'importTextPara': 'txt',
               'importMozilla': 'html',
               'importXbel': 'xml',
               'importOldTreeLine': 'trl',
               'importTreePad': 'hjt',
               'importXml': 'xml',
               'importOdfText': 'odt'}

oldDateTimeConv = {'d': '%-d', 'dd': '%d', 'ddd': '%a', 'dddd': '%A',
                   'M': '%-m', 'MM': '%m', 'MMM': '%b', 'MMMM': '%B',
                   'yy': '%y', 'yyyy': '%Y',
                   'H': '%-H', 'HH': '%H', 'h': '%-I', 'hh': '%I',
                   'm': '%-M', 'mm': '%M', 's': '%-S', 'ss': '%S',
                   'zzz': '%f', 'AP': '%p', 'ap': '%p'}
bookmarkFolderTypeName = _('FOLDER')
bookmarkLinkTypeName = _('BOOKMARK')
bookmarkSeparatorTypeName = _('SEPARATOR')
bookmarkLinkFieldName = _('Link')
textFieldName = _('Text')
genericXmlTextFieldName = 'Element_Data'
htmlUnescapeDict = {'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"'}


class ImportControl:
    """Control file imports of alt file types.
    """
    def __init__(self, pathObj=None):
        """Initialize the import control object.

        Arguments:
            pathObj -- the path object to import if given, o/w prompt user
        """
        self.pathObj = pathObj
        self.errorMessage = ''
        # below members for old TreeLine file imports
        self.treeLineImportVersion = []
        self.treeLineRootAttrib = {}
        self.treeLineOldFieldAttr = {}

    def interactiveImport(self, addWarning=False):
        """Prompt the user for import type & proceed with import.

        Return the structure if import is successful, otherwise None
        Arguments:
            addWarning - if True, add non-valid file warning to dialog
        """
        dialog = miscdialogs.RadioChoiceDialog(_('Import File'),
                                               _('Choose Import Method'),
                                               methods.items(),
                                               QApplication.
                                               activeWindow())
        if addWarning:
            fileName = self.pathObj.name
            dialog.addLabelBox(_('Invalid File'),
                               _('"{0}" is not a valid TreeLine file.\n\n'
                                 'Use an import filter?').format(fileName))
        if dialog.exec_() != QDialog.Accepted:
            return None
        method = dialog.selectedButton()
        if not self.pathObj:
            filters = ';;'.join((globalref.fileFilters[fileFilters[method]],
                                 globalref.fileFilters['all']))
            defaultFilePath = str(globalref.mainControl.defaultPathObj(True))
            filePath, selFltr = QFileDialog.getOpenFileName(QApplication.
                                                   activeWindow(),
                                                   _('TreeLine - Import File'),
                                                   defaultFilePath, filters)
            if not filePath:
                return None
            self.pathObj = pathlib.Path(filePath)
        self.errorMessage = ''
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            structure = getattr(self, method)()
            QApplication.restoreOverrideCursor()
        except IOError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(QApplication.activeWindow(),
                                      'TreeLine',
                                      _('Error - could not read file {0}').
                                      format(self.pathObj))
            return None
        except UnicodeDecodeError:
            prevEncoding = globalref.localTextEncoding
            globalref.localTextEncoding = 'utf-8'
            structure = getattr(self, method)()
            globalref.localTextEncoding = prevEncoding
            QApplication.restoreOverrideCursor()
        if not structure:
            message = _('Error - improper format in {0}').format(self.pathObj)
            if self.errorMessage:
                message = '{0}\n{1}'.format(message, self.errorMessage)
                self.errorMessage = ''
            QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                message)
        return structure

    def importTabbedText(self):
        """Import a file with tabbed title structure.

        Return the structure if import is successful, otherwise None
        """
        structure = treestructure.TreeStructure(addDefaults=True,
                                                addSpots=False)
        formatRef = structure.childList[0].formatRef
        structure.removeNodeDictRef(structure.childList[0])
        structure.childList = []
        nodeList = []
        with self.pathObj.open(encoding=globalref.localTextEncoding) as f:
            for line in f:
                text = line.strip()
                if text:
                    level = line.count('\t', 0, len(line) - len(line.lstrip()))
                    node = treenode.TreeNode(formatRef)
                    node.setTitle(text)
                    structure.addNodeDictRef(node)
                    nodeList.append((node, level))
        if nodeList and structure.loadChildNodeLevels(nodeList):
                structure.generateSpots(None)
                return structure
        return None

    def importTableCsvLevels(self):
        """Import a CSV-delimited table file with level column, header row.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure(addSpots=False)
        tableFormat = nodeformat.NodeFormat(_('TABLE'), structure.treeFormats)
        structure.treeFormats.addTypeIfMissing(tableFormat)
        nodeList = []
        with self.pathObj.open(newline='',
                               encoding=globalref.localTextEncoding) as f:
            reader = csv.reader(f)
            try:
                headings = [self.correctFieldName(name) for name in
                            next(reader)][1:]
                if not headings:
                    self.errorMessage = (_('No headings found'));
                    return None   # abort
                tableFormat.addFieldList(headings, True, True)
                for entries in reader:
                    if entries:
                        node = treenode.TreeNode(tableFormat)
                        structure.addNodeDictRef(node)
                        try:
                            level = int(entries.pop(0))
                        except ValueError:
                            self.errorMessage = (_('Invalid level number on '
                                                   'line {0}').
                                                 format(reader.line_num))
                            return None   # abort
                        nodeList.append((node, level))
                        try:
                            for heading in headings:
                                node.data[heading] = entries.pop(0)
                        except IndexError:
                            pass    # fewer entries than headings is OK
                        if entries:
                            self.errorMessage = (_('Too many entries on '
                                                   'Line {0}').
                                                 format(reader.line_num))
                            return None   # abort if too few headings
            except csv.Error:
                self.errorMessage = (_('Bad CSV format on Line {0}').
                                     format(reader.line_num))
                return None   # abort
        if nodeList:
            if structure.loadChildNodeLevels(nodeList):
                structure.generateSpots(None)
                return structure
            self.errorMessage = (_('Invalid level structure'))
        return None

    def importTableCsv(self):
        """Import a file with a CSV-delimited table with header row.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure(addDefaults=True,
                                                addSpots=False)
        tableFormat = nodeformat.NodeFormat(_('TABLE'), structure.treeFormats)
        structure.treeFormats.addTypeIfMissing(tableFormat)
        with self.pathObj.open(newline='',
                               encoding=globalref.localTextEncoding) as f:
            reader = csv.reader(f)
            try:
                headings = [self.correctFieldName(name) for name in
                            next(reader)]
                if not headings:
                    self.errorMessage = (_('No headings found'));
                    return None   # abort
                tableFormat.addFieldList(headings, True, True)
                for entries in reader:
                    if entries:
                        node = treenode.TreeNode(tableFormat)
                        structure.childList[0].childList.append(node)
                        structure.addNodeDictRef(node)
                        try:
                            for heading in headings:
                                node.data[heading] = entries.pop(0)
                        except IndexError:
                            pass    # fewer entries than headings is OK
                        if entries:
                            self.errorMessage = (_('Too many entries on '
                                                   'Line {0}').
                                                 format(reader.line_num))
                            return None   # abort if too few headings
            except csv.Error:
                self.errorMessage = (_('Bad CSV format on Line {0}').
                                     format(reader.line_num))
                return None   # abort
        structure.generateSpots(None)
        return structure

    def importTableTabbed(self):
        """Import a file with a tab-delimited table with header row.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure(addDefaults=True,
                                                addSpots=False)
        tableFormat = nodeformat.NodeFormat(_('TABLE'), structure.treeFormats)
        structure.treeFormats.addTypeIfMissing(tableFormat)
        with self.pathObj.open(encoding=globalref.localTextEncoding) as f:
            headings = [self.correctFieldName(name) for name in
                        f.readline().split('\t')]
            tableFormat.addFieldList(headings, True, True)
            lineNum = 1
            for line in f:
                lineNum += 1
                if line.strip():
                    entries = line.split('\t')
                    node = treenode.TreeNode(tableFormat)
                    structure.childList[0].childList.append(node)
                    structure.addNodeDictRef(node)
                    try:
                        for heading in headings:
                            node.data[heading] = entries.pop(0)
                    except IndexError:
                        pass    # fewer entries than headings is OK
                    if entries:
                        self.errorMessage = (_('Too many entries on Line {0}').
                                             format(lineNum))
                        return None   # abort if too few headings
        structure.generateSpots(None)
        return structure

    @staticmethod
    def correctFieldName(name):
        """Return the field name with any illegal characters removed.

        Arguments:
            name -- the name to modify
        """
        name = re.sub(r'[^\w_\-.]', '_', name.strip())
        if not name:
            return 'X'
        if not name[0].isalpha() or name[:3].lower() == 'xml':
            name = 'X' + name
        return name

    def importTextLines(self):
        """Import a text file, creating one node per line.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure(addDefaults=True,
                                                addSpots=False)
        nodeFormat = structure.childList[0].formatRef
        structure.removeNodeDictRef(structure.childList[0])
        structure.childList = []
        with self.pathObj.open(encoding=globalref.localTextEncoding) as f:
            for line in f:
                line = line.strip()
                if line:
                    node = treenode.TreeNode(nodeFormat)
                    structure.childList.append(node)
                    structure.addNodeDictRef(node)
                    node.data[nodeformat.defaultFieldName] = line
        structure.generateSpots(None)
        return structure

    def importTextPara(self):
        """Import a text file, creating one node per paragraph.

        Blank line delimited.
        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure(addDefaults=True,
                                                addSpots=False)
        nodeFormat = structure.childList[0].formatRef
        structure.removeNodeDictRef(structure.childList[0])
        structure.childList = []
        with self.pathObj.open(encoding=globalref.localTextEncoding) as f:
            text = f.read()
        paraList = text.split('\n\n')
        for para in paraList:
            para = para.strip()
            if para:
                node = treenode.TreeNode(nodeFormat)
                structure.childList.append(node)
                structure.addNodeDictRef(node)
                node.data[nodeformat.defaultFieldName] = para
        structure.generateSpots(None)
        return structure

    def importOldTreeLine(self):
        """Import an old TreeLine File (1.x or 2.x).

        Return the structure if import is successful, otherwise None.
        """
        tree = ElementTree.ElementTree()
        try:
            tree.parse(str(self.pathObj))
        except ElementTree.ParseError:
            tree = None
        if not tree or not tree.getroot().get('item') == 'y':
            fileObj = self.pathObj.open('rb')
            # decompress before decrypt to support TreeLine 1.4 and earlier
            fileObj, compressed = globalref.mainControl.decompressFile(fileObj)
            fileObj, encrypted = globalref.mainControl.decryptFile(fileObj)
            if not fileObj:
                return None
            if encrypted and not compressed:
                fileObj, compressed = (globalref.mainControl.
                                       decompressFile(fileObj))
            if compressed or encrypted:
                tree = ElementTree.ElementTree()
                try:
                    tree.parse(fileObj)
                except ElementTree.ParseError:
                    tree = None
            fileObj.close()
            if not tree or not tree.getroot().get('item') == 'y':
                return None
        version = tree.getroot().get('tlversion', '').split('.')
        try:
            self.treeLineImportVersion = [int(i) for i in version]
        except ValueError:
            pass
        self.treeLineRootAttrib = self.convertPrintData(tree.getroot().attrib)
        structure = treestructure.TreeStructure()
        idRefDict = {}
        linkList = []
        self.loadOldTreeLineNode(tree.getroot(), structure, idRefDict,
                                 linkList, None)
        self.convertOldNodes(structure)
        linkRe = re.compile(r'<a [^>]*href="#(.*?)"[^>]*>.*?</a>', re.I | re.S)
        for node, fieldName in linkList:
            text = node.data[fieldName]
            startPos = 0
            while True:
                match = linkRe.search(text, startPos)
                if not match:
                    break
                newId = idRefDict.get(match.group(1), '')
                if newId:
                    text = text[:match.start(1)] + newId + text[match.end(1):]
                startPos = match.start(1)
            node.data[fieldName] = text
        structure.generateSpots(None)
        if nodeformat.FileInfoFormat.typeName in structure.treeFormats:
            fileFormat = structure.treeFormats[nodeformat.FileInfoFormat.
                                               typeName]
            structure.treeFormats.fileInfoFormat.duplicateFileInfo(fileFormat)
            del structure.treeFormats[nodeformat.FileInfoFormat.typeName]
        structure.treeFormats.updateDerivedRefs()
        for nodeFormat in structure.treeFormats.values():
            nodeFormat.updateLineParsing()
        return structure

    def loadOldTreeLineNode(self, element, structure, idRefDict, linkList,
                            parent=None):
        """Recursively load an old TreeLine ElementTree node and its children.

        Arguments:
            element -- an ElementTree node
            structure -- a ref to the new tree structure
            idRefDict -- a dict to relate old to new unique node IDs
            linkList -- internal link list ref with (node, fieldname) tuples
            parent  -- the parent TreeNode (None for the root node only)
        """
        try:
            typeFormat = structure.treeFormats[element.tag]
        except KeyError:
            formatData = self.convertOldNodeFormat(element.attrib)
            typeFormat = nodeformat.NodeFormat(element.tag,
                                               structure.treeFormats,
                                               formatData)
            structure.treeFormats[element.tag] = typeFormat
            self.treeLineOldFieldAttr[typeFormat.name] = {}
        if element.get('item') == 'y':
            node = treenode.TreeNode(typeFormat)
            oldId = element.attrib.get('uniqueid', '')
            if oldId:
                idRefDict[oldId] = node.uId
            if parent:
                parent.childList.append(node)
            else:
                structure.childList.append(node)
            structure.nodeDict[node.uId] = node
            cloneAttr = element.attrib.get('clones', '')
            if cloneAttr:
                for cloneId in cloneAttr.split(','):
                    if cloneId in idRefDict:
                        cloneNode = structure.nodeDict[idRefDict[cloneId]]
                        node.data = cloneNode.data.copy()
                        break
        else:     # bare format (no nodes)
            node = None
        for child in element:
            if child.get('item') and node:
                self.loadOldTreeLineNode(child, structure, idRefDict,
                                         linkList, node)
            else:
                if node and child.text:
                    node.data[child.tag] = child.text
                    if child.get('linkcount'):
                        linkList.append((node, child.tag))
                if child.tag not in typeFormat.fieldDict:
                    fieldData = self.convertOldFieldFormat(child.attrib)
                    oldFormatDict = self.treeLineOldFieldAttr[typeFormat.name]
                    oldFormatDict[child.tag] = fieldData
                    typeFormat.addField(child.tag, fieldData)

    def convertPrintData(self, attrib):
        """Return JSON print data from old root attributes.

        Arguments:
            attrib -- old root print data attributes
        """
        for key in ('printlines', 'printwidowcontrol', 'printportrait'):
            if key in attrib:
                attrib[key] = not attrib[key].startswith('n')
        for key in ('printindentfactor', 'printpaperwidth', 'printpaperheight',
                    'printheadermargin', 'printfootermargin',
                    'printcolumnspace'):
            if key in attrib:
                attrib[key] = float(attrib[key])
        if 'printmargins' in attrib:
            attrib['printmargins'] = [float(margin) for margin in
                                      attrib['printmargins'].split()]
        if 'printnumcolumns' in attrib:
            attrib['printnumcolumns'] = int(attrib['printnumcolumns'])
        return attrib

    def convertOldNodeFormat(self, attrib):
        """Return JSON format data from old node format attributes.

        Arguments:
            attrib -- old node format attrib dict
        """
        for key in ('spacebetween', 'formathtml', 'bullets', 'tables'):
            if key in attrib:
                attrib[key] = attrib[key].startswith('y')
        attrib['titleline'] = attrib.get('line0', '')
        lineKeyRe = re.compile(r'line\d+$')
        lineNums = sorted([int(key[4:]) for key in attrib.keys()
                           if lineKeyRe.match(key)])
        if lineNums and lineNums[0] == 0:
            del lineNums[0]
        attrib['outputlines'] = [attrib['line{0}'.format(keyNum)] for
                                 keyNum in lineNums]
        if self.treeLineImportVersion < [1, 9]:  # for very old TL versions
            attrib['spacebetween'] = not (self.treeLineRootAttrib.
                                          get('nospace', '').startswith('y'))
            attrib['formathtml'] = not (self.treeLineRootAttrib.
                                        get('nohtml', '').startswith('y'))
        return attrib

    def convertOldFieldFormat(self, attrib):
        """Return JSON format data from old field format attributes.

        Arguments:
            attrib -- old field node format attrib dict
        """
        fieldType = attrib.get('type', '')
        if fieldType:
            attrib['fieldtype'] = fieldType
        fieldFormat = attrib.get('format', '')
        if self.treeLineImportVersion < [1, 9]:  # for very old TL versions
            if fieldType in ('URL', 'Path', 'ExecuteLink', 'Email'):
                attrib['oldfieldtype'] = fieldType
                fieldType = 'ExternalLink'
                attrib['fieldtype'] = fieldType
            if fieldType == 'Date':
                fieldFormat = fieldFormat.replace('w', 'd')
                fieldFormat = fieldFormat.replace('m', 'M')
            if fieldType == 'Time':
                fieldFormat = fieldFormat.replace('M', 'm')
                fieldFormat = fieldFormat.replace('s', 'z')
                fieldFormat = fieldFormat.replace('S', 's')
                fieldFormat = fieldFormat.replace('AA', 'AP')
                fieldFormat = fieldFormat.replace('aa', 'ap')
        if 'lines' in attrib:
            attrib['lines'] = int(attrib['lines'])
        if 'sortkeynum' in attrib:
            attrib['sortkeynum'] = int(attrib['sortkeynum'])
        if 'sortkeydir' in attrib:
            attrib['sortkeyfwd'] = not attrib['sortkeydir'].startswith('r')
        if 'evalhtml' in attrib:
            attrib['evalhtml'] = attrib['evalhtml'].startswith('y')
        if fieldType in ('Date', 'Time', 'DateTime'):
            origFormat = fieldFormat
            fieldFormat = ''
            while origFormat:
                replLen = 4
                while replLen > 0:
                    if origFormat[:replLen] in oldDateTimeConv:
                        fieldFormat += oldDateTimeConv[origFormat[:replLen]]
                        origFormat = origFormat[replLen:]
                        break
                    replLen -= 1
                if replLen == 0:
                    fieldFormat += origFormat[0]
                    origFormat = origFormat[1:]
        if fieldFormat:
            attrib['format'] = fieldFormat
        return attrib

    def convertOldNodes(self, structure):
        """Convert node data to new date and time formats.

        Arguments:
            structure -- the ref structure containing the data
        """
        for node in structure.nodeDict.values():
            for field in node.formatRef.fields():
                text = node.data.get(field.name, '')
                if text:
                    if field.typeName in ('Date', 'DateTime'):
                        text = text.replace('/', '-')
                    if field.typeName in ('Time', 'DateTime'):
                        text = text + '.000000'
                    if self.treeLineImportVersion < [1, 9]:  # very old TL ver
                        oldFormatDict = self.treeLineOldFieldAttr[node.
                                                                formatRef.name]
                        oldFieldAttr = oldFormatDict[field.name]
                        if (field.typeName == 'Text' and not
                            oldFieldAttr.get('html', '').startswith('y')):
                            text = text.strip()
                            text = xml.sax.saxutils.escape(text)
                            text = text.replace('\n', '<br />')
                        elif (field.typeName == 'ExternalLink' and
                              oldFieldAttr.get('oldfieldtype', '')):
                            oldType = oldFieldAttr['oldfieldtype']
                            linkAltField = oldFieldAttr.get('linkalt', '')
                            dispName = node.data.get(linkAltField, '')
                            if not dispName:
                                dispName = text
                            if oldType == 'URL':
                                if not urltools.extractScheme(text):
                                    text = urltools.replaceScheme('http', text)
                            elif oldType == 'Path':
                                text = urltools.replaceScheme('file', text)
                            elif oldType == 'ExecuteLink':
                                if urltools.isRelative(text):
                                    fullPath = urltools.which(text)
                                    if fullPath:
                                        text = fullPath
                                text = urltools.replaceScheme('file', text)
                            elif oldType == 'Email':
                                text = urltools.replaceScheme('mailto', text)
                            text = '<a href="{0}">{1}</a>'.format(text,
                                                                  dispName)
                        elif field.typeName == 'InternalLink':
                            linkAltField = oldFieldAttr.get('linkalt', '')
                            dispName = node.data.get(linkAltField, '')
                            if not dispName:
                                dispName = text
                            uniqueId = text.strip().split('\n', 1)[0]
                            uniqueId = uniqueId.replace(' ', '_').lower()
                            uniqueId = re.sub(r'[^a-zA-Z0-9_-]+', '', uniqueId)
                            text = '<a href="#{0}">{1}</a>'.format(uniqueId,
                                                                   dispName)
                        elif field.typeName == 'Picture':
                            text = '<img src="{0}" />'.format(text)
                    node.data[field.name] = text

    def importTreePad(self):
        """Import a Treepad file, text nodes only.

        Return the model if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure(addDefaults=True,
                                                addSpots=False)
        structure.removeNodeDictRef(structure.childList[0])
        structure.childList = []
        tpFormat = structure.treeFormats[treeformats.defaultTypeName]
        tpFormat.addFieldList([textFieldName], False, True)
        tpFormat.fieldDict[textFieldName].changeType('SpacedText')
        try:
            with self.pathObj.open(encoding=globalref.localTextEncoding) as f:
                textList = f.read().split('<end node> 5P9i0s8y19Z')
        except UnicodeDecodeError:
            with self.pathObj.open(encoding='latin-1') as f:
                textList = f.read().split('<end node> 5P9i0s8y19Z')
        except UnicodeDecodeError:
            return None
        nodeList = []
        for text in textList:
            text = text.strip()
            if text:
                try:
                    text = text.split('<node>', 1)[1].lstrip()
                    lines = text.split('\n')
                    title = lines[0]
                    level = int(lines[1])
                    lines = lines[2:]
                except (ValueError, IndexError):
                    return None
                node =  treenode.TreeNode(tpFormat)
                node.data[nodeformat.defaultFieldName] = title
                node.data[textFieldName] = '\n'.join(lines)
                node.level = level
                nodeList.append(node)
                structure.addNodeDictRef(node)
        parentList = []
        for node in nodeList:
            if node.level != 0:
                parentList = parentList[:node.level]
                node.parent = parentList[-1]
                parentList[-1].childList.append(node)
            parentList.append(node)
        structure.childList = [nodeList[0]]
        structure.generateSpots(None)
        return structure

    def importXml(self):
        """Import a non-treeline generic XML file.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure()
        tree = ElementTree.ElementTree()
        try:
            tree.parse(str(self.pathObj))
            self.loadXmlNode(tree.getroot(), structure, None)
        except ElementTree.ParseError:
            return None
        for elemFormat in structure.treeFormats.values():
            if not elemFormat.getTitleLine():  # fix formats if required
                elemFormat.changeTitleLine(elemFormat.name)
                for fieldName in elemFormat.fieldNames():
                    elemFormat.addOutputLine('{0}="{{*{1}*}}"'.
                                             format(fieldName, fieldName))
            if not elemFormat.fieldDict:
                elemFormat.addField(genericXmlTextFieldName)
        if structure.childList:
            structure.generateSpots(None)
            return structure
        return None

    def loadXmlNode(self, element, structure, parent=None):
        """Recursively load a generic XML ElementTree node and its children.

        Arguments:
            element -- an XML ElementTree node
            structure -- a ref to the TreeLine structure
            parent -- the parent TreeNode (None for the root node only)
        """
        elemFormat = structure.treeFormats.get(element.tag, None)
        if not elemFormat:
            elemFormat = nodeformat.NodeFormat(element.tag,
                                               structure.treeFormats)
            structure.treeFormats[element.tag] = elemFormat
        node = treenode.TreeNode(elemFormat)
        structure.addNodeDictRef(node)
        if not parent:
            parent = structure
        parent.childList.append(node)
        if element.text and element.text.strip():
            if genericXmlTextFieldName not in elemFormat.fieldDict:
                elemFormat.addFieldList([genericXmlTextFieldName], True, True)
            text = element.text.strip()
            text = xml.sax.saxutils.escape(text)
            text = text.replace('\n', '<br />')
            node.data[genericXmlTextFieldName] = text
        for key, value in element.items():
            elemFormat.addFieldIfNew(key)
            node.data[key] = value
        for child in element:
            self.loadXmlNode(child, structure, node)

    def importOdfText(self):
        """Import an ODF format text file outline.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure(addDefaults=True,
                                                addSpots=False)
        structure.removeNodeDictRef(structure.childList[0])
        structure.childList = []
        odfFormat = structure.treeFormats[treeformats.defaultTypeName]
        odfFormat.addField(textFieldName)
        odfFormat.changeOutputLines(['<b>{{*{0}*}}</b>'.
                                     format(nodeformat.defaultFieldName),
                                     '{{*{0}*}}'.format(textFieldName)])
        odfFormat.formatHtml = True
        try:
            with zipfile.ZipFile(str(self.pathObj), 'r') as f:
                text = f.read('content.xml')
        except (zipfile.BadZipFile, KeyError):
            return None
        try:
            rootElement = ElementTree.fromstring(text)
        except ElementTree.ParseError:
            return None
        nameSpace = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
        headerTag = '{0}h'.format(nameSpace)
        paraTag = '{0}p'.format(nameSpace)
        numRegExp = re.compile(r'.*?(\d+)$')
        parents = [structure]
        prevLevel = 0
        for elem in rootElement.iter():
            if elem.tag == headerTag:
                style = elem.get('{0}style-name'.format(nameSpace), '')
                try:
                    level = int(numRegExp.match(style).group(1))
                except AttributeError:
                    return None
                if level < 1 or level > prevLevel + 1:
                    return None
                parents = parents[:level]
                node = treenode.TreeNode(odfFormat)
                structure.addNodeDictRef(node)
                parents[-1].childList.append(node)
                node.data[nodeformat.defaultFieldName] = ''.join(elem.
                                                                itertext())
                parents.append(node)
                prevLevel = level
            elif elem.tag == paraTag:
                text = ''.join(elem.itertext())
                origText = node.data.get(textFieldName, '')
                if origText:
                    text = '{0}<br />{1}'.format(origText, text)
                node.data[textFieldName] = text
        structure.generateSpots(None)
        return structure

    def createBookmarkFormat(self):
        """Return a set of node formats for bookmark imports.
        """
        treeFormats = treeformats.TreeFormats()
        folderFormat = nodeformat.NodeFormat(bookmarkFolderTypeName,
                                             treeFormats, addDefaultField=True)
        folderFormat.iconName = 'folder_3'
        treeFormats[folderFormat.name] = folderFormat
        linkFormat = nodeformat.NodeFormat(bookmarkLinkTypeName, treeFormats,
                                           addDefaultField=True)
        linkFormat.addField(bookmarkLinkFieldName,
                            {'fieldtype': 'ExternalLink'})
        linkFormat.addOutputLine('{{*{0}*}}'.format(bookmarkLinkFieldName))
        linkFormat.iconName = 'bookmark'
        treeFormats[linkFormat.name] = linkFormat
        sepFormat = nodeformat.NodeFormat(bookmarkSeparatorTypeName,
                                          treeFormats, {'formathtml': True},
                                          True)
        sepFormat.changeTitleLine('------------------')
        sepFormat.changeOutputLines(['<hr>'])
        treeFormats[sepFormat.name] = sepFormat
        return treeFormats

    def importMozilla(self):
        """Import an HTML mozilla-format bookmark file.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure()
        structure.treeFormats = self.createBookmarkFormat()
        with self.pathObj.open(encoding='utf-8') as f:
            text = f.read()
        try:
            handler = HtmlBookmarkHandler(structure)
            handler.feed(text)
            handler.close()
        except ValueError:
            return None
        structure.generateSpots(None)
        return structure

    def importXbel(self):
        """Import an XBEL format bookmark file.

        Return the structure if import is successful, otherwise None.
        """
        structure = treestructure.TreeStructure()
        structure.treeFormats = self.createBookmarkFormat()
        tree = ElementTree.ElementTree()
        try:
            tree.parse(str(self.pathObj))
        except ElementTree.ParseError:
            return None
        self.loadXbelNode(tree.getroot(), structure, None)
        if structure.childList:
            structure.generateSpots(None)
            return structure
        return None

    def loadXbelNode(self, element, structure, parent=None):
        """Recursively load an XBEL ElementTree node and its children.

        Arguments:
            element -- an XBEL ElementTree node
            model -- a ref to the TreeLine model
            parent  -- the parent TreeNode (None for the root node only)
        """
        if element.tag in ('xbel', 'folder'):
            node = treenode.TreeNode(structure.
                                     treeFormats[bookmarkFolderTypeName])
            structure.addNodeDictRef(node)
            if parent:
                parent.childList.append(node)
            else:
                structure.childList.append(node)
            for child in element:
                self.loadXbelNode(child, structure, node)
        elif element.tag == 'bookmark':
            node = treenode.TreeNode(structure.
                                     treeFormats[bookmarkLinkTypeName])
            structure.addNodeDictRef(node)
            parent.childList.append(node)
            link = element.get('href').strip()
            if link:
                node.data[bookmarkLinkFieldName] = ('<a href="{0}">{1}</a>'.
                                                    format(link, link))
            for child in element:
                self.loadXbelNode(child, structure, node)
        elif element.tag == 'title':
            parent.setTitle(element.text)
        elif element.tag == 'separator':
            node = treenode.TreeNode(structure.
                                     treeFormats[bookmarkSeparatorTypeName])
            structure.addNodeDictRef(node)
            parent.childList.append(node)
        else:   # unsupported tags
            pass


class HtmlBookmarkHandler(html.parser.HTMLParser):
    """Handler to parse HTML mozilla bookmark format.
    """
    def __init__(self, structure):
        """Initialize the HTML parser object.

        Arguments:
            structure -- a reference to the tree structure
        """
        super().__init__()
        self.structure = structure
        rootNode = treenode.TreeNode(self.structure.
                                     treeFormats[bookmarkFolderTypeName])
        rootNode.data[nodeformat.defaultFieldName] = _('Bookmarks')
        self.structure.addNodeDictRef(rootNode)
        self.structure.childList = [rootNode]
        self.currentNode = rootNode
        self.parents = []
        self.text = ''

    def handle_starttag(self, tag, attrs):
        """Called by the reader at each open tag.

        Arguments:
            tag -- the tag label
            attrs -- any tag attributes
        """
        if tag == 'dt' or tag == 'h1':      # start any entry
            self.text = ''
        elif tag == 'dl':    # start indent
            self.parents.append(self.currentNode)
            self.currentNode = None
        elif tag == 'h3':    # start folder
            if not self.parents:
                raise ValueError
            self.currentNode = treenode.TreeNode(self.structure.
                                           treeFormats[bookmarkFolderTypeName])
            self.structure.addNodeDictRef(self.currentNode)
            self.parents[-1].childList.append(self.currentNode)
        elif tag == 'a':     # start link
            if not self.parents:
                raise ValueError
            self.currentNode = treenode.TreeNode(self.structure.
                                             treeFormats[bookmarkLinkTypeName])
            self.structure.addNodeDictRef(self.currentNode)
            self.parents[-1].childList.append(self.currentNode)
            for name, value in attrs:
                if name == 'href':
                    link = '<a href="{0}">{0}</a>'.format(value)
                    self.currentNode.data[bookmarkLinkFieldName] = link
        elif tag == 'hr':     # separator
            if not self.parents:
                raise ValueError
            node = treenode.TreeNode(self.structure.
                                     treeFormats[bookmarkSeparatorTypeName])
            self.structure.addNodeDictRef(node)
            self.parents[-1].childList.append(node)
            self.currentNode = None

    def handle_endtag(self, tag):
        """Called by the reader at each end tag.

        Arguments:
            tag -- the tag label
        """
        if tag == 'dl':      # end indented section
            self.parents = self.parents[:-1]
            self.currentNode = None
        elif tag == 'h3' or tag == 'a':    # end folder or link
            if not self.currentNode:
                raise ValueError
            self.currentNode.data[nodeformat.defaultFieldName] = self.text
        elif tag == 'h1':    # end main title
            self.structure.childList[0].data[nodeformat.
                                             defaultFieldName] = self.text

    def handle_data(self, data):
        """Called by the reader to process text.

        Arguments:
            data -- the new text
        """
        self.text += data

    def handle_entityref(self, name):
        """Convert escaped entity ref to char.

        Arguments:
            name -- the name of the escaped entity
        """
        self.text += htmlUnescapeDict.get(name, '')
