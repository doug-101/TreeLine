#!/usr/bin/env python3

#******************************************************************************
# gettrans.py, updates Qt-style translation files from PyQt source
#              uses gettext-style markings and filenames as contexts
#
# Copyright (C) 2020, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import argparse
import pathlib
import ast
import collections
import copy
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


class TransItem:
    """Class to hold data for and output a single translation string.
    """
    def __init__(self, contextName, lineNum, srcText, comment=''):
        """Initialize the tramslation string item.

        Arguments:
            contextName -- a string containing the filename-based context
            lineNum -- the line of the first occurrence in the source code
            srcText -- the untranslated source text string
            comment -- optional comment from source as a guide to translation
        """
        self.contextName = contextName
        self.lineNum = lineNum
        self.srcText = srcText
        self.comment = comment
        self.transType = 'unfinished'
        self.transText = ''

    def xmlLines(self):
        """Return a list of XML output lines for this item.
        """
        lines = ['    <message>',
                 f'        <location filename="{self.contextName}.py" '
                 f'line="{self.lineNum}"/>',
                 f'        <source>{escape(self.srcText)}</source>']
        if self.comment:
            lines.append(f'        <comment>{self.comment}</comment>')
        transType = f' type="{self.transType}"' if self.transType else ''
        lines.extend([f'        <translation{transType}>'
                      f'{escape(self.transText)}</translation>',
                      '    </message>'])
        return lines


def readSource(path, sourceDict):
    """Read strings to be translated from the a single source file path.

    Updates the give source dict with any results from this context.
    Arguments:
        path -- the source file path to read
        sourceDict -- the dictionary to add a context dict to with results
    """
    with path.open(encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src)

    contextDict = collections.OrderedDict()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
            (node.func.id == '_' or node.func.id == 'N_')):
            try:
                text = node.args[0].value
                text.replace  # throw exception if not a string
                comment = node.args[1].value if len(node.args) > 1 else ''
            except AttributeError:
                continue   # skip if no string is present
            item = TransItem(path.stem, node.lineno, text, comment)
            contextDict.setdefault((text, comment), item)
    if contextDict:    # only add the context dictionary if there are results
        sourceDict[path.stem] = contextDict
        if verbose:
            print('Read', len(contextDict), 'items from', path.name)


def readXml(root, sourceDict, keepObsolete=True):
    """Read the XML for a language file starting from an elemant tree root.

    Returns tuple of an outputDict with results by context and
    a globalDict with all translations to search for matches.
    Arguments:
        root -- the ET root to read
        sourceDict -- the dict with source strings for comparison
        keepObsolete -- save obsolete strings (no longer in source) if True
    """
    outputDict = collections.OrderedDict()
    globalDict = {}
    for contextNode in root.findall('context'):
        contextName = contextNode.find('name').text
        currentDict = collections.OrderedDict()
        numObsolete = 0
        for msgNode in contextNode.findall('message'):
            try:
                lineNum = int(msgNode.find('location').attrib['line'])
            except AttributeError:
                # .ts files converted from .qm files have no locations and
                # line numbers
                lineNum = 0
            srcText = msgNode.find('source').text
            commentNode = msgNode.find('comment')
            comment = commentNode.text if commentNode is not None else ''
            item = TransItem(contextName, lineNum, srcText, comment)
            transNode = msgNode.find('translation')
            item.transType = transNode.attrib.get('type', '')
            item.transText = transNode.text if transNode.text else ''
            try:
                sourceItem = sourceDict[contextName][(srcText, comment)]
            except KeyError:   # string wasn't found in source dict
                if item.transType != 'obsolete':
                    item.transType = 'obsolete'
                    numObsolete += 1
            else:
                item.lineNum = sourceItem.lineNum
                if item.transType == 'obsolete':
                    item.transType = 'unfinished'
            if keepObsolete or item.transType != 'obsolete':
                currentDict[(srcText, comment)] = item
            if item.transText:
                globalDict[(srcText, comment)] = item
        outputDict[contextName] = currentDict
        if verbose and numObsolete:
            print(f'   {numObsolete} newly obsolete strings in '
                  f'{contextName}.py')
    return (outputDict, globalDict)


def addMissingItems(sourceDict, outputDict):
    """Add items from source dict that are missing from output dict.

    Arguments:
        sourceDict -- the source translations to add from
        outputDict -- the result dict to modify
    """
    for contextName, sourceItems in sourceDict.items():
        numNew = 0
        currentDict = outputDict.get(contextName, {})
        if not currentDict:
            outputDict[contextName] = currentDict
        for sourceItem in sourceItems.values():
            if (verbose and (sourceItem.srcText, sourceItem.comment) not in
                currentDict):
                numNew += 1
            currentDict.setdefault((sourceItem.srcText, sourceItem.comment),
                                   copy.copy(sourceItem))
        if verbose and numNew:
            print(f'   {numNew} new strings added from {contextName}.py')


def updateFromGlobal(outputDict, globalDict):
    """Search strings from all contexts and add translations if they match.

    Arguments:
        outputDict -- the result dict to modify
        globalDict -- the overall dict to search
    """
    for contextName, currentDict in outputDict.items():
        numUpdates = 0
        for item in currentDict.values():
            if not item.transText:
                match = globalDict.get((item.srcText, item.comment))
                if match:
                    item.transText = match.transText
                    numUpdates += 1
        if verbose and numUpdates:
            print(f'   {numUpdates} translations in {contextName} copied '
                  'from other strings')


def outputXml(outputDict, path, lang):
    """Return a list of output lines for a language file.

    Arguments:
        outputDict -- the result strings to output
        path -- the translation file path to write the file
        lang -- the language code for the file header
    """
    outputLines = ['<?xml version="1.0" encoding="utf-8"?>',
                   f'<!DOCTYPE TS><TS version="1.1" language="{lang}">']
    for contextName, currentDict in outputDict.items():
        outputLines.extend(['<context>',
                            f'    <name>{contextName}</name>'])
        for item in currentDict.values():
            outputLines.extend(item.xmlLines())
        outputLines.append('</context>')
    outputLines.append('</TS>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(outputLines))


verbose = False

def main():
    """Main program entry function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('sourceDir', type=pathlib.Path,
                        help='directory of input source files read with *.py')
    parser.add_argument('translateDir', type=pathlib.Path,
                        help='directory of *.ts translation files to update')
    parser.add_argument('--no-obsolete', action='store_true',
                        help='drop all obsolete strings')
    parser.add_argument('-R', '--recursive', action='store_true',
                        help='recursively scan the directories')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase output messages')
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    sourceDict = collections.OrderedDict()
    pyGlob = '**/*.py' if args.recursive else '*.py'
    for sourcePath in sorted(args.sourceDir.glob(pyGlob)):
        readSource(sourcePath, sourceDict)
    if verbose:
        print('-----------------------------------------')

    tsGlob = '**/*.ts' if args.recursive else '*.ts'
    for transPath in sorted(args.translateDir.glob(tsGlob)):
        try:
            root = ET.parse(transPath).getroot()
        except ET.ParseError:
            print('Warning: nothing read from', transPath)
            root = ET.ElementTree(ET.Element('TS')).getroot()
        lang = root.attrib.get('language')
        if not lang:   # get from filename if not in header
            pathParts = transPath.stem.split('_')
            if len(pathParts) > 1:
                lang = pathParts[-1]
            if not lang:
                lang = 'xx'
        if verbose:
            print(f'For language code "{lang}":')
        outputDict, globalDict = readXml(root, sourceDict,
                                         not args.no_obsolete)
        addMissingItems(sourceDict, outputDict)

        updateFromGlobal(outputDict, globalDict)

        outputXml(outputDict, transPath, lang)


if __name__ == '__main__':
    """Main program entry point.
    """
    main()
