#!/usr/bin/env python3

#****************************************************************************
# spellcheck.py, provides classes for spell check interfaces and dialogs,
# including interfaces to aspell, ispell, hunspell.
#
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#*****************************************************************************

import re
import sys
import subprocess
import collections
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics, QTextCursor
from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QMessageBox, QPushButton, QTextEdit, QVBoxLayout)
import undo
import globalref

_guessRe = re.compile('[&?] (\S+) \d+ (\d+): (.+)')
_noGuessRe = re.compile('# (\S+) (\d+)')


class SpellCheckInterface:
    """Interfaces with aspell, ispell or hunspell and stores session hooks.
    """
    def __init__(self, spellPath='', langCode=''):
        """Create initial hooks to outside program.
        
        Arguments:
            spellPath -- use to find engine executable if given
            langCode -- language code to pass to aspell if given
        """
        engineOptions = collections.OrderedDict()
        engineOptions.update([('aspell', ['-a -H --encoding=utf-8']),
                              ('ispell', ['-a -h -Tutf8', '-a']),
                              ('hunspell', ['-a -H -i utf-8'])])
        langPrefix = {'aspell': 'l', 'ispell': 'd', 'hunspell': 'd'}
        if spellPath:
            newEngineOptions = {}
            for engine in engineOptions.keys():
                if engine in spellPath:
                    newEngineOptions[spellPath] = engineOptions[engine]
            engineOptions = newEngineOptions
        for engine, options in engineOptions.items():
            if langCode:
                options.insert(0, '{0} -{1} {2}'.format(options[0],
                                                        langPrefix[engine],
                                                        langCode))
            for option in options:
                cmd = '{0} {1}'.format(engine, option)
                try:
                    p = subprocess.Popen(cmd, shell=True,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    self.stdIn = p.stdin
                    self.stdOut = p.stdout
                    self.stdOut.readline()  # read header
                    # set terse mode (no correct returns)
                    self.stdIn.write(b'!\n')
                    self.stdIn.flush()
                    return
                except IOError:
                    pass
        raise SpellCheckError('Could not initialize aspell, ispell or '
                              'hunspell')
 
    def checkLine(self, line, skipWords=None):
        """Check one (and only one) line of text.

        Return a list of tuples, each with the mispelled word, position in
        the line, and a list of suggestions.
        Arguments:
            line -- the text string to check
            skipWords -- a set of words to ignore if given
        """
        if not skipWords:
            skipWords = set()
        self.stdIn.write('^{0}\n'.format(line).encode('utf-8'))
        self.stdIn.flush()
        outputs = [self.stdOut.readline()]
        while outputs[-1].strip():
            outputs.append(self.stdOut.readline())
        results = []
        for output in outputs:
            output = output.decode('utf-8').strip()
            match = _guessRe.match(output)
            if match:
                guesses = match.group(3).split(', ')
            else:
                match = _noGuessRe.match(output)
                guesses = []
            if match:
                word = match.group(1)
                if word not in skipWords:
                    wordPos = int(match.group(2)) - 1
                    # work around unicode bug in older versions of aspell
                    while (line[wordPos:wordPos + len(word)] != word and
                           wordPos > 0):
                        wordPos -= 1
                    results.append((word, wordPos, guesses))
        return results

    def close(self):
        """Shut down hooks to outside program.
        """
        self.stdIn.close()
        self.stdOut.close()

    def acceptWord(self, word):
        """Accept given word for the remainder of this session.

        Arguments:
            word -- the word to accept
        """
        self.stdIn.write('@{0}\n'.format(word).encode('utf-8'))
        self.stdIn.flush()

    def addToDict(self, word, lowCase=False):
        """Add word to spell check engine's dictionary.

        Arguments:
            word -- the word to add
            lowCase -- if True, add the word as a lower case word
        """
        if lowCase:
            self.stdIn.write('&{0}\n'.format(word).encode('utf-8'))
        else:
            self.stdIn.write('*{0}\n'.format(word).encode('utf-8'))
        self.stdIn.write(b'#\n')  # saves dict
        self.stdIn.flush()


class SpellCheckError(Exception):
    """Exception class for errors interfacing with the spell check engine.
    """
    pass


# console test for the spell check engine interface
if __name__ == '__main__':
    try:
        sp = SpellCheckInterface()
    except SpellCheckError:
        print('Error - could not initialize aspell, ispell or hunspell')
        sys.exit()
    while True:
        s = input('Enter line-> ').strip()
        if not s:
            sys.exit()
        if s.startswith('Accept->'):
            sp.acceptWord(s[8:])
        elif s.startswith('Add->'):
            sp.addToDict(s[5:])
        elif s.startswith('AddLow->'):
            sp.addToDict(s[8:], True)
        else:
            for word, pos, suggests in sp.checkLine(s):
                print('{0} @{1}: {2}\n'.format(word, pos, ', '.join(suggests)))
    sp.close()


class SpellCheckOperation:
    """Feeds tree node text to the spell check dialog.
    """
    def __init__(self, controlRef):
        """Initialize the spell check engine interface.

        Arguments:
            controlRef - the local control
        """
        self.controlRef = controlRef
        self.selectModel = controlRef.currentSelectionModel()
        self.currentNode = None
        self.currentField = ''
        self.lineNum = 0
        self.textLine = ''
        parentWidget = QApplication.activeWindow()
        path = globalref.miscOptions['SpellCheckPath']
        while True:
            try:
                self.spellCheckInterface = SpellCheckInterface(path,
                                                               self.controlRef.
                                                               spellCheckLang)
                return
            except SpellCheckError:
                if path:
                    path = ''
                else:
                    if sys.platform.startswith('win'):
                        prompt = (_('Could not find either aspell.exe, '
                                    'ispell.exe or hunspell.exe\n'
                                    'Browse for location?'))
                        ans = QMessageBox.warning(parentWidget,
                                                      _('Spell Check Error'),
                                                      prompt,
                                                      QMessageBox.Yes |
                                                      QMessageBox.Cancel,
                                                      QMessageBox.Yes)
                        if ans == QMessageBox.Cancel:
                            raise
                        title = _('Locate aspell.exe, ipsell.exe or '
                                  'hunspell.exe')
                        path, fltr = QFileDialog.getOpenFileName(parentWidget,
                                                          title, '',
                                                          _('Program (*.exe)'))
                        if path:
                            path = path[:-4]
                            if ' ' in path:
                                path = '"{0}"'.format(path)
                            globalref.miscOptions.changeValue('SpellCheckPath',
                                                              path)
                            globalref.miscOptions.writeFile()
                    else:
                        prompt = (_('TreeLine Spell Check Error\nMake sure '
                                    'aspell, ispell or hunspell is installed'))
                        QMessageBox.warning(parentWidget, 'TreeLine',
                                                  prompt)
                        raise

    def spellCheck(self):
        """Spell check starting with the selected branches.
        """
        parentWidget = QApplication.activeWindow()
        spellCheckDialog = SpellCheckDialog(self.spellCheckInterface,
                                            parentWidget)
        spellCheckDialog.misspellFound.connect(self.updateSelection)
        spellCheckDialog.changeRequest.connect(self.changeNode)
        origBranches = self.selectModel.uniqueBranches()
        result = (spellCheckDialog.
                  startSpellCheck(self.textLineGenerator(origBranches)))
        self.selectModel.selectNodes(origBranches, expandParents = True)
        if result and origBranches[0].parent:
            prompt = (_('Finished checking the branch\n'
                        'Continue from the root branch?'))
            ans = QMessageBox.information(parentWidget,
                                          _('TreeLine Spell Check'), prompt,
                                          QMessageBox.Yes | QMessageBox.No)
            if ans == QMessageBox.Yes:
                generator = self.textLineGenerator([self.controlRef.model.
                                                    root])
                result = spellCheckDialog.startSpellCheck(generator)
                self.selectModel.selectNodes(origBranches,
                                             expandParents = True)
            else:
                result = False
        if result:
            QMessageBox.information(parentWidget, _('TreeLine Spell Check'),
                                    _('Finished spell checking'))

    def updateSelection(self):
        """Change the tree selection to the node with a misspelled word.
        """
        self.selectModel.selectNode(self.currentNode, expandParents = True)

    def changeNode(self, newTextLine):
        """Replace the current text line in the current node.

        Arguments:
            newTextLine -- the new text to use
        """
        undo.DataUndo(self.currentNode.modelRef.undoList, self.currentNode)
        textLines = (self.currentNode.data.get(self.currentField, '').
                     split('\n'))
        textLines[self.lineNum] = newTextLine
        self.currentNode.data[self.currentField] = '\n'.join(textLines)
        self.controlRef.updateTreeNode(self.currentNode)

    def textLineGenerator(self, branches):
        """Yield next line to be checked.

        Arguments:
            branches -- a list of branch parent nodes to check.
        """
        for parent in branches:
            for self.currentNode in parent.descendantGen():
                for self.currentField in (self.currentNode.nodeFormat().
                                          fieldNames()):
                    text = self.currentNode.data.get(self.currentField, '')
                    if text:
                        for self.lineNum, self.textLine in \
                                            enumerate(text.split('\n')):
                            yield self.textLine


class SpellCheckDialog(QDialog):
    """Dialog to perform and control the spell check operation.
    """
    misspellFound = pyqtSignal()
    changeRequest = pyqtSignal(str)
    def __init__(self, spellCheckInterface, parent=None):
        """Create the dialog.

        Arguments:
            spellCheckInterface -- a reference to the spell engine interface
            parent -- the parent dialog
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Spell Check'))
        self.spellCheckInterface = spellCheckInterface
        self.textLineIter = None
        self.textLine = ''
        self.replaceAllDict = {}
        self.tmpIgnoreWords = set()
        self.word = ''
        self.postion = 0

        topLayout = QHBoxLayout(self)
        leftLayout = QVBoxLayout()
        topLayout.addLayout(leftLayout)
        wordBox = QGroupBox(_('Not in Dictionary'))
        leftLayout.addWidget(wordBox)
        wordLayout = QVBoxLayout(wordBox)
        label = QLabel(_('Word:'))
        wordLayout.addWidget(label)
        self.wordEdit = QLineEdit()
        wordLayout.addWidget(self.wordEdit)
        self.wordEdit.textChanged.connect(self.updateFromWord)
        wordLayout.addSpacing(5)
        label = QLabel(_('Context:'))
        wordLayout.addWidget(label)
        self.contextEdit = SpellContextEdit()
        wordLayout.addWidget(self.contextEdit)
        self.contextEdit.textChanged.connect(self.updateFromContext)

        suggestBox = QGroupBox(_('Suggestions'))
        leftLayout.addWidget(suggestBox)
        suggestLayout =  QVBoxLayout(suggestBox)
        self.suggestList = QListWidget()
        suggestLayout.addWidget(self.suggestList)
        self.suggestList.itemDoubleClicked.connect(self.replace)

        rightLayout = QVBoxLayout()
        topLayout.addLayout(rightLayout)
        ignoreButton = QPushButton(_('Ignor&e'))
        rightLayout.addWidget(ignoreButton)
        ignoreButton.clicked.connect(self.ignore)
        ignoreAllButton = QPushButton(_('&Ignore All'))
        rightLayout.addWidget(ignoreAllButton)
        ignoreAllButton.clicked.connect(self.ignoreAll)
        rightLayout.addStretch()
        addButton = QPushButton(_('&Add'))
        rightLayout.addWidget(addButton)
        addButton.clicked.connect(self.add)
        addLowerButton = QPushButton(_('Add &Lowercase'))
        rightLayout.addWidget(addLowerButton)
        addLowerButton.clicked.connect(self.addLower)
        rightLayout.addStretch()
        replaceButton = QPushButton(_('&Replace'))
        rightLayout.addWidget(replaceButton)
        replaceButton.clicked.connect(self.replace)
        self.replaceAllButton = QPushButton(_('Re&place All'))
        rightLayout.addWidget(self.replaceAllButton)
        self.replaceAllButton.clicked.connect(self.replaceAll)
        rightLayout.addStretch()
        cancelButton = QPushButton(_('&Cancel'))
        rightLayout.addWidget(cancelButton)
        cancelButton.clicked.connect(self.reject)
        self.widgetDisableList = [ignoreButton, ignoreAllButton, addButton,
                                  addLowerButton, self.suggestList]
        self.fullDisableList = (self.widgetDisableList +
                                [self.replaceAllButton, self.wordEdit])

    def startSpellCheck(self, textLineIter):
        """Spell check text lines given in the iterator.

        Block execution except for the dialog if mispellings are found.
        Return True if spell check completes, False if cancelled.
        Arguments:
            textLineIter -- an iterator of text lines to check
        """
        self.textLineIter = textLineIter
        try:
            self.textLine = next(self.textLineIter)
        except StopIteration:
            return True
        if self.spellCheck():
            if self.exec_() == QDialog.Rejected:
                return False
        return True

    def continueSpellCheck(self):
        """Check lines, starting with current line.

        Exit the dialog if there are no more lines to check.
        """
        if not self.spellCheck():
            self.accept()

    def spellCheck(self):
        """Step through the iterator and spell check the lines.

        If results found, update the dialog with the results and return True.
        Return false if the end of the iterator is reached.
        """
        while True:
            results = self.spellCheckInterface.checkLine(self.textLine,
                                                         self.tmpIgnoreWords)
            if results:
                self.word, self.position, suggestions = results[0]
                newWord = self.replaceAllDict.get(self.word, '')
                if newWord:
                    self.textLine = self.replaceWord(newWord)
                    self.changeRequest.emit(self.textLine)
                else:
                    self.misspellFound.emit()
                    self.setWord(suggestions)
                    return True
            try:
                self.textLine = next(self.textLineIter)
                self.tmpIgnoreWords.clear()
            except StopIteration:
                return False

    def setWord(self, suggestions):
        """Set dialog contents from the checked line and spell check results.
        
        Arguments:
            suggestions -- a list of suggested replacement words
        """
        self.wordEdit.blockSignals(True)
        self.wordEdit.setText(self.word)
        self.wordEdit.blockSignals(False)
        self.contextEdit.blockSignals(True)
        self.contextEdit.setPlainText(self.textLine)
        self.contextEdit.setSelection(self.position,
                                      self.position + len(self.word))
        self.contextEdit.blockSignals(False)
        self.suggestList.clear()
        self.suggestList.addItems(suggestions)
        self.suggestList.setCurrentItem(self.suggestList.item(0))
        for widget in self.fullDisableList:
            widget.setEnabled(True)

    def replaceWord(self, newWord):
        """Return textLine with word replaced with newWord.
        
        Arguments:
            newWord -- the replacement word
        """
        return (self.textLine[:self.position] + newWord +
                self.textLine[self.position + len(self.word):])

    def ignore(self):
        """Set word to ignored (this check only) and continue spell check.
        """
        self.tmpIgnoreWords.add(self.word)
        self.continueSpellCheck()

    def ignoreAll(self):
        """Add to dictionary's ignore list and continue spell check.
        """
        self.spellCheckInterface.acceptWord(self.word)
        self.continueSpellCheck()

    def add(self):
        """Add misspelling to dictionary and continue spell check"""
        self.spellCheckInterface.addToDict(self.word, False)
        self.continueSpellCheck()

    def addLower(self):
        """Add misspelling to dictionary as lowercase and continue spell check.
        """
        self.spellCheckInterface.addToDict(self.word, True)
        self.continueSpellCheck()

    def replace(self):
        """Replace misspelled word with suggestion or context edit box
        
        Then continue spell check.
        """
        if self.suggestList.isEnabled():
            newWord = self.suggestList.currentItem().text()
            self.textLine = self.replaceWord(newWord)
        else:
            self.textLine = self.contextEdit.toPlainText()
        self.changeRequest.emit(self.textLine)
        self.continueSpellCheck()

    def replaceAll(self):
        """Replace misspelled word with suggestion or word edit (in future too).
        
        Stores changed word in replaceAllDict and continues spell check.
        """
        if self.suggestList.isEnabled():
            newWord = self.suggestList.currentItem().text()
        else:
            newWord = self.wordEdit.text()
        self.textLine = self.replaceWord(newWord)
        self.replaceAllDict[self.word] = newWord
        self.changeRequest.emit(self.textLine)
        self.continueSpellCheck()

    def updateFromWord(self):
        """Update dialog after word line editor change.
        
        Disables suggests and ignore/add controls. Updates the context editor.
        """
        for widget in self.widgetDisableList:
            widget.setEnabled(False)
        newWord = self.wordEdit.text()
        self.suggestList.clearSelection()
        self.contextEdit.blockSignals(True)
        self.contextEdit.setPlainText(self.replaceWord(newWord))
        self.contextEdit.setSelection(self.position,
                                      self.position + len(newWord))
        self.contextEdit.blockSignals(False)

    def updateFromContext(self):
        """Update dialog after context editor change.
        
        Disables controls except for replace.
        """
        for widget in self.fullDisableList:
            widget.setEnabled(False)
        self.suggestList.clearSelection()


class SpellContextEdit(QTextEdit):
    """Editor for spell check word context.
    
    Sets the size hint to 3 lines and simplifies selction.
    """
    def __init__(self, parent=None):
        """Create the editor.

        Arguments:
            parent -- the parent widget
        """
        super().__init__(parent)
        self.setTabChangesFocus(True)

    def sizeHint(self):
        """Set prefered size of 3 lines long.
        """
        fontHeight = QFontMetrics(self.currentFont()).lineSpacing()
        return QSize(QTextEdit.sizeHint(self).width(),
                            fontHeight * 3)

    def setSelection(self, fromPos, toPos):
        """Select the given range in first paragraph.
        
        Arguments:
            fromPos -- the starting position
            toPos -- the ending position
        """
        cursor = self.textCursor()
        cursor.setPosition(fromPos)
        cursor.setPosition(toPos, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
