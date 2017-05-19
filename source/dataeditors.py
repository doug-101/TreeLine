#!/usr/bin/env python3

#******************************************************************************
# dataeditors.py, provides classes for data editors in the data edit view
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import xml.sax.saxutils
import os.path
import sys
import re
import subprocess
from PyQt5.QtCore import (QDate, QDateTime, QPoint, QPointF, QSize, QTime, Qt,
                          pyqtSignal)
from PyQt5.QtGui import (QBrush, QFont, QPainter, QPainterPath, QPixmap,
                         QTextCursor, QTextDocument)
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication,
                             QButtonGroup, QCalendarWidget, QCheckBox,
                             QColorDialog, QComboBox, QDialog, QFileDialog,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMenu, QPushButton, QRadioButton, QScrollArea,
                             QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)
import dataeditview
import fieldformat
# import urltools
import globalref
import optiondefaults

multipleSpaceRegEx = re.compile(r' {2,}')


class PlainTextEditor(QTextEdit):
    """An editor widget for multi-line plain text fields.
    """
    dragLinkEnabled = False
    contentsChanged = pyqtSignal(QWidget)
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setPalette(QApplication.palette())
        self.setStyleSheet('QTextEdit {border: 2px solid palette(highlight)}')
        self.setTabChangesFocus(True)
        self.cursorPositionChanged.connect(self.updateActions)
        self.selectionChanged.connect(self.updateActions)
        self.allActions = parent.parent().allActions
        self.modified = False
        self.textChanged.connect(self.signalUpdate)

    def setContents(self, text):
        """Set the contents of the editor to text.

        Arguments:
            text - the new text contents for the editor
        """
        self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(False)

    def contents(self):
        """Return the editor text contents.
        """
        return self.toPlainText()

    def hasSelectedText(self):
        """Return True if text is selected.
        """
        return self.textCursor().hasSelection()

    def setCursorPoint(self, point):
        """Set the cursor to the given point.

        Arguments:
            point -- the QPoint for the new cursor position
        """
        self.setTextCursor(self.cursorForPosition(self.mapFromGlobal(point)))

    def resetCursor(self):
        """Set the cursor to end for tab-focus use.
        """
        self.moveCursor(QTextCursor.End)

    def signalUpdate(self):
        """Signal the delegate to update the model based on an editor change.
        """
        self.modified = True
        self.contentsChanged.emit(self)

    def disableActions(self):
        """Reset action availability after focus is lost.
        """
        self.allActions['EditCut'].setEnabled(True)
        self.allActions['EditCopy'].setEnabled(True)
        mime = QApplication.clipboard().mimeData()
        self.allActions['EditPaste'].setEnabled(len(mime.data('text/xml') or
                                                    mime.data('text/plain'))
                                                > 0)

    def updateActions(self):
        """Set availability of context menu actions.
        """
        hasSelection = self.textCursor().hasSelection()
        self.allActions['EditCut'].setEnabled(hasSelection)
        self.allActions['EditCopy'].setEnabled(hasSelection)
        mime = QApplication.clipboard().mimeData()
        self.allActions['EditPaste'].setEnabled(len(mime.data('text/plain'))
                                                > 0)

    def contextMenuEvent(self, event):
        """Override popup menu to add global actions.

        Arguments:
            event -- the menu event
        """
        menu = QMenu(self)
        menu.addAction(self.allActions['FormatSelectAll'])
        menu.addSeparator()
        menu.addAction(self.allActions['EditCut'])
        menu.addAction(self.allActions['EditCopy'])
        menu.addAction(self.allActions['EditPaste'])
        menu.exec_(event.globalPos())

    def focusInEvent(self, event):
        """Set availability and update format actions.

        Arguments:
            event -- the focus event
        """
        super().focusInEvent(event)
        self.updateActions()

    def focusOutEvent(self, event):
        """Reset format actions on focus loss if not focusing a menu.

        Arguments:
            event -- the focus event
        """
        super().focusOutEvent(event)
        if event.reason() != Qt.PopupFocusReason:
            self.disableActions()

    def hideEvent(self, event):
        """Reset format actions when the editor is hidden.

        Arguments:
            event -- the hide event
        """
        self.disableActions()
        super().hideEvent(event)


class HtmlTextEditor(PlainTextEditor):
    """An editor for HTML fields, plain text with HTML insert commands.
    """
    htmlFontSizes = ('small', '', 'large', 'x-large', 'xx-large')
    dragLinkEnabled = True
    inLinkSelectMode = pyqtSignal(bool)
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.intLinkDialog = None
        self.addedIntLinkFlag = False
        self.allActions['FormatBoldFont'].triggered.connect(self.setBoldFont)
        self.allActions['FormatItalicFont'].triggered.connect(self.
                                                              setItalicFont)
        self.allActions['FormatUnderlineFont'].triggered.connect(self.
                                                              setUnderlineFont)
        self.allActions['FormatFontSize'].parent().triggered.connect(self.
                                                                   setFontSize)
        self.allActions['FormatFontSize'].triggered.connect(self.
                                                          showFontSizeMenu)
        self.allActions['FormatFontColor'].triggered.connect(self.setFontColor)
        self.allActions['FormatExtLink'].triggered.connect(self.setExtLink)
        self.allActions['FormatIntLink'].triggered.connect(self.setIntLink)

    def insertTagText(self, prefix, suffix):
        """Insert given tag text and maintain the original selection.

        Arguments:
            prefix -- the opening tag
            suffix -- the closing tag
        """
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        text = '{0}{1}{2}'.format(prefix, cursor.selectedText(), suffix)
        self.insertPlainText(text)
        cursor.setPosition(start + len(prefix))
        cursor.setPosition(end + len(prefix), QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def setBoldFont(self, checked):
        """Insert tags for a bold font.

        Arguments:
            checked -- current toggle state of the control
        """
        try:
            if self.hasFocus() and checked:
                self.insertTagText('<b>', '</b>')
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setItalicFont(self, checked):
        """Insert tags for an italic font.

        Arguments:
            checked -- current toggle state of the control
        """
        try:
            if self.hasFocus() and checked:
                self.insertTagText('<i>', '</i>')
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setUnderlineFont(self, checked):
        """Insert tags for an underline font.

        Arguments:
            checked -- current toggle state of the control
        """
        try:
            if self.hasFocus() and checked:
                self.insertTagText('<u>', '</u>')
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setFontSize(self, action):
        """Set the font size of the selection or the current setting.

        Arguments:
            action -- the sub-menu action that was picked
        """
        try:
            if self.hasFocus():
                actions = self.allActions['FormatFontSize'].parent().actions()
                sizeNum = actions.index(action)
                size = HtmlTextEditor.htmlFontSizes[sizeNum]
                self.insertTagText('<span style="font-size:{0}">'.format(size),
                                   '</span>')
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setFontColor(self):
        """Set the font color of the selection or the current setting.

        Prompt the user for a color using a dialog.
        """
        try:
            if self.hasFocus():
                charFormat = self.currentCharFormat()
                oldColor = charFormat.foreground().color()
                newColor = QColorDialog.getColor(oldColor, self)
                if newColor.isValid():
                    self.insertTagText('<span style="color:{0}">'.
                                       format(newColor.name()), '</span>')
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setExtLink(self):
        """Add or modify an extrnal web link at the cursor.
        """
        try:
            if self.hasFocus():
                dialog = ExtLinkDialog(False, self)
                address, name = self.selectLink()
                if address.startswith('#'):
                    address = name = ''
                dialog.setFromComponents(address, name)
                if dialog.exec_() == QDialog.Accepted:
                    self.insertPlainText(dialog.htmlText())
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setIntLink(self):
        """Show dialog to add or modify an internal node link at the cursor.
        """
        try:
            if self.hasFocus():
                self.intLinkDialog = IntLinkDialog(False, self)
                address, name = self.selectLink()
                if address.startswith('#'):
                    address = address.lstrip('#')
                else:
                    address = ''
                self.intLinkDialog.setFromComponents(address, name)
                self.intLinkDialog.setModal(True)
                self.intLinkDialog.finished.connect(self.insertInternalLink)
                self.intLinkDialog.show()
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def insertInternalLink(self, resultCode):
        """Add or modify an internal node link based on dialog approval.

        Arguments:
            resultCode -- the result from the dialog (OK or cancel)
        """
        if resultCode == QDialog.Accepted:
            self.addedIntLinkFlag = True
            self.insertPlainText(self.intLinkDialog.htmlText())
        self.intLinkDialog = None

    def setLinkFromNode(self, node):
        """Set the current internal link from a clicked node.

        Arguments:
            node -- the node to set the unique ID from
        """
        if self.intLinkDialog:
            self.intLinkDialog.setFromNode(node)

    def selectLink(self):
        """Select the full link at the cursor, return link data.

        Any links at the cursor or partially selected are fully selected.
        Returns a tuple of the link address and name, or a tuple with empty
        strings if none are found.
        """
        cursor = self.textCursor()
        anchor = cursor.anchor()
        position = cursor.position()
        for match in fieldformat.linkRegExp.finditer(self.toPlainText()):
            start = match.start()
            end = match.end()
            if start < anchor < end or start < position < end:
                address, name = match.groups()
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
                return (address, name)
        return ('', cursor.selectedText())

    def addDroppedUrl(self, urlText):
        """Add the URL link that was dropped on this editor from the view.

        Arguments:
            urlText -- the text of the link
        """
        name = urltools.shortName(urlText)
        text = '<a href="{0}">{1}</a>'.format(urlText, name)
        self.insertPlainText(text)

    def disableActions(self):
        """Set format actions to unavailable.
        """
        super().disableActions()
        self.allActions['FormatBoldFont'].setEnabled(False)
        self.allActions['FormatItalicFont'].setEnabled(False)
        self.allActions['FormatUnderlineFont'].setEnabled(False)
        self.allActions['FormatFontSize'].parent().setEnabled(False)
        self.allActions['FormatFontColor'].setEnabled(False)
        self.allActions['FormatExtLink'].setEnabled(False)
        self.allActions['FormatIntLink'].setEnabled(False)

    def updateActions(self):
        """Set editor format actions to available and update toggle states.
        """
        super().updateActions()
        boldFontAct = self.allActions['FormatBoldFont']
        boldFontAct.setEnabled(True)
        boldFontAct.setChecked(False)
        italicAct = self.allActions['FormatItalicFont']
        italicAct.setEnabled(True)
        italicAct.setChecked(False)
        underlineAct = self.allActions['FormatUnderlineFont']
        underlineAct.setEnabled(True)
        underlineAct.setChecked(False)
        fontSizeSubMenu = self.allActions['FormatFontSize'].parent()
        fontSizeSubMenu.setEnabled(True)
        for action in fontSizeSubMenu.actions():
            action.setChecked(False)
        self.allActions['FormatFontColor'].setEnabled(True)
        self.allActions['FormatExtLink'].setEnabled(True)
        self.allActions['FormatIntLink'].setEnabled(True)

    def showFontSizeMenu(self):
        """Show a context menu for font size at this edit box.
        """
        if self.hasFocus():
            rect = self.rect()
            pt = self.mapToGlobal(QPoint(rect.center().x(),
                                                rect.bottom()))
            self.allActions['FormatFontSize'].parent().popup(pt)

    def contextMenuEvent(self, event):
        """Override popup menu to add formatting and global actions.

        Arguments:
            event -- the menu event
        """
        menu = QMenu(self)
        menu.addAction(self.allActions['FormatBoldFont'])
        menu.addAction(self.allActions['FormatItalicFont'])
        menu.addAction(self.allActions['FormatUnderlineFont'])
        menu.addSeparator()
        menu.addMenu(self.allActions['FormatFontSize'].parent())
        menu.addAction(self.allActions['FormatFontColor'])
        menu.addSeparator()
        menu.addAction(self.allActions['FormatExtLink'])
        menu.addAction(self.allActions['FormatIntLink'])
        menu.addSeparator()
        menu.addAction(self.allActions['FormatSelectAll'])
        menu.addSeparator()
        menu.addAction(self.allActions['EditCut'])
        menu.addAction(self.allActions['EditCopy'])
        menu.addAction(self.allActions['EditPaste'])
        menu.exec_(event.globalPos())

    def hideEvent(self, event):
        """Close the internal link dialog when the editor is hidden.

        Arguments:
            event -- the hide event
        """
        if self.intLinkDialog:
            self.intLinkDialog.close()
            self.intLinkDialog = None
        super().hideEvent(event)


class RichTextEditor(HtmlTextEditor):
    """An editor widget for multi-line wysiwyg rich text fields.
    """
    fontPointSizes = []
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.setAcceptRichText(True)
        if not RichTextEditor.fontPointSizes:
            doc = QTextDocument()
            doc.setDefaultFont(self.font())
            for sizeName in HtmlTextEditor.htmlFontSizes:
                if sizeName:
                    doc.setHtml('<span style="font-size:{0}">text</span>'.
                                format(sizeName))
                    pointSize = (QTextCursor(doc).charFormat().font().
                                 pointSize())
                else:
                    pointSize = self.font().pointSize()
                RichTextEditor.fontPointSizes.append(pointSize)
        self.allActions['FormatClearFormat'].triggered.connect(self.
                                                               setClearFormat)
        self.allActions['EditPastePlain'].triggered.connect(self.pastePlain)

    def setContents(self, text):
        """Set the contents of the editor to text.

        Arguments:
            text - the new text contents for the editor
        """
        self.blockSignals(True)
        self.setHtml(text)
        self.blockSignals(False)

    def contents(self):
        """Return simplified HTML code for the editor contents.

        Replace Unicode line feeds with HTML breaks, escape <, >, &,
        and replace some rich formatting with HTML tags.
        """
        doc = self.document()
        block = doc.begin()
        result = ''
        while block.isValid():
            if result:
                result += '<br />\n'
            fragIter = block.begin()
            while not fragIter.atEnd():
                text = xml.sax.saxutils.escape(fragIter.fragment().text())
                text = text.replace('\u2028', '<br />\n')
                charFormat = fragIter.fragment().charFormat()
                if charFormat.fontWeight() >= QFont.Bold:
                    text = '<b>{0}</b>'.format(text)
                if charFormat.fontItalic():
                    text = '<i>{0}</i>'.format(text)
                size = charFormat.font().pointSize()
                if size != self.font().pointSize():
                    closeSize = min((abs(size - i), i) for i in
                                    RichTextEditor.fontPointSizes)[1]
                    sizeNum = RichTextEditor.fontPointSizes.index(closeSize)
                    htmlSize = HtmlTextEditor.htmlFontSizes[sizeNum]
                    if htmlSize:
                        text = ('<span style="font-size:{0}">{1}</span>'.
                                format(htmlSize, text))
                if charFormat.anchorHref():
                    text = '<a href="{0}">{1}</a>'.format(charFormat.
                                                          anchorHref(), text)
                else:
                    # ignore underline and font color for links
                    if charFormat.fontUnderline():
                        text = '<u>{0}</u>'.format(text)
                    if (charFormat.foreground().color().name() !=
                        block.charFormat().foreground().color().name()):
                        text = ('<span style="color:{0}">{1}</span>'.
                                format(charFormat.foreground().color().name(),
                                       text))
                result += text
                fragIter += 1
            block = block.next()
        return result

    def setBoldFont(self, checked):
        """Set the selection or the current setting to a bold font.

        Arguments:
            checked -- current toggle state of the control
        """
        try:
            if self.hasFocus():
                if checked:
                    self.setFontWeight(QFont.Bold)
                else:
                    self.setFontWeight(QFont.Normal)
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setItalicFont(self, checked):
        """Set the selection or the current setting to an italic font.

        Arguments:
            checked -- current toggle state of the control
        """
        try:
            if self.hasFocus():
                self.setFontItalic(checked)
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setUnderlineFont(self, checked):
        """Set the selection or the current setting to an underlined font.

        Arguments:
            checked -- current toggle state of the control
        """
        try:
            if self.hasFocus():
                self.setFontUnderline(checked)
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setFontSize(self, action):
        """Set the font size of the selection or the current setting.

        Arguments:
            action -- the sub-menu action that was picked
        """
        try:
            if self.hasFocus():
                actions = self.allActions['FormatFontSize'].parent().actions()
                sizeNum = actions.index(action)
                pointSize = RichTextEditor.fontPointSizes[sizeNum]
                charFormat = self.currentCharFormat()
                charFormat.setFontPointSize(pointSize)
                self.setCurrentCharFormat(charFormat)
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setFontColor(self):
        """Set the font color of the selection or the current setting.

        Prompt the user for a color using a dialog.
        """
        try:
            if self.hasFocus():
                charFormat = self.currentCharFormat()
                oldColor = charFormat.foreground().color()
                newColor = QColorDialog.getColor(oldColor, self)
                if newColor.isValid():
                    charFormat.setForeground(QBrush(newColor))
                    self.setCurrentCharFormat(charFormat)
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setClearFormat(self):
        """Clear the current or selected text formatting.
        """
        try:
            if self.hasFocus():
                self.setCurrentFont(self.font())
                charFormat = self.currentCharFormat()
                charFormat.clearForeground()
                charFormat.setAnchor(False)
                charFormat.setAnchorHref('')
                self.setCurrentCharFormat(charFormat)
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def setExtLink(self):
        """Add or modify an extrnal web link at the cursor.
        """
        try:
            if self.hasFocus():
                dialog = ExtLinkDialog(False, self)
                address, name = self.selectLink()
                if address.startswith('#'):
                    address = name = ''
                dialog.setFromComponents(address, name)
                if dialog.exec_() == QDialog.Accepted:
                    if self.textCursor().hasSelection():
                        self.insertHtml(dialog.htmlText())
                    else:
                        self.insertHtml(dialog.htmlText() + ' ')
        except RuntimeError:
            pass    # avoid calling a deleted C++ editor object

    def insertInternalLink(self, resultCode):
        """Add or modify an internal node link based on dialog approval.

        Arguments:
            resultCode -- the result from the dialog (OK or cancel)
        """
        if resultCode == QDialog.Accepted:
            self.addedIntLinkFlag = True
            if self.textCursor().hasSelection():
                self.insertHtml(self.intLinkDialog.htmlText())
            else:
                self.insertHtml(self.intLinkDialog.htmlText() + ' ')
        self.intLinkDialog = None

    def selectLink(self):
        """Select the full link at the cursor, return link data.

        Any links at the cursor or partially selected are fully selected.
        Returns a tuple of the link address and name, or a tuple with empty
        strings if none are found.
        """
        cursor = self.textCursor()
        if not cursor.hasSelection() and not cursor.charFormat().anchorHref():
            return ('', '')
        selectText = cursor.selection().toPlainText()
        anchorCursor = QTextCursor(self.document())
        anchorCursor.setPosition(cursor.anchor())
        cursor.clearSelection()
        if cursor < anchorCursor:
            anchorCursor, cursor = cursor, anchorCursor
        position = cursor.position()
        address = name = ''
        if anchorCursor.charFormat().anchorHref():
            fragIter = anchorCursor.block().begin()
            while not (fragIter.fragment().contains(anchorCursor.position()) or
                    fragIter.fragment().contains(anchorCursor.position() - 1)):
                fragIter += 1
            fragment = fragIter.fragment()
            anchorCursor.setPosition(fragment.position())
            address = fragment.charFormat().anchorHref()
            name = fragment.text()
        if cursor.charFormat().anchorHref():
            fragIter = cursor.block().begin()
            while not (fragIter.fragment().contains(cursor.position()) or
                       fragIter.fragment().contains(cursor.position() - 1)):
                fragIter += 1
            fragment = fragIter.fragment()
            position = fragment.position() + fragment.length()
            address = fragment.charFormat().anchorHref()
            name = fragment.text()
        if not name:
            name = selectText.split('\n')[0]
        cursor.setPosition(anchorCursor.position())
        cursor.setPosition(position, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        return (address, name)

    def addDroppedUrl(self, urlText):
        """Add the URL link that was dropped on this editor from the view.

        Arguments:
            urlText -- the text of the link
        """
        name = urltools.shortName(urlText)
        text = '<a href="{0}">{1}</a>'.format(urlText, name)
        if not self.textCursor().hasSelection():
            text += ' '
        self.insertHtml(text)

    def pastePlain(self):
        """Paste non-formatted text from the clipboard.
        """
        text = QApplication.clipboard().mimeData().text()
        if text and self.hasFocus():
            self.insertPlainText(text)

    def disableActions(self):
        """Set format actions to unavailable.
        """
        super().disableActions()
        self.allActions['FormatClearFormat'].setEnabled(False)
        self.allActions['EditPastePlain'].setEnabled(False)

    def updateActions(self):
        """Set editor format actions to available and update toggle states.
        """
        super().updateActions()
        self.allActions['FormatBoldFont'].setChecked(self.fontWeight() ==
                                                   QFont.Bold)
        self.allActions['FormatItalicFont'].setChecked(self.fontItalic())
        self.allActions['FormatUnderlineFont'].setChecked(self.fontUnderline())
        fontSizeSubMenu = self.allActions['FormatFontSize'].parent()
        pointSize = int(self.fontPointSize())
        try:
            sizeNum = RichTextEditor.fontPointSizes.index(pointSize)
        except ValueError:
            sizeNum = 1   # default size
        fontSizeSubMenu.actions()[sizeNum].setChecked(True)
        self.allActions['FormatClearFormat'].setEnabled(True)
        mime = QApplication.clipboard().mimeData()
        self.allActions['EditPastePlain'].setEnabled(len(mime.
                                                         data('text/plain'))
                                                     > 0)

    def contextMenuEvent(self, event):
        """Override popup menu to add formatting and global actions.

        Arguments:
            event -- the menu event
        """
        menu = QMenu(self)
        menu.addAction(self.allActions['FormatBoldFont'])
        menu.addAction(self.allActions['FormatItalicFont'])
        menu.addAction(self.allActions['FormatUnderlineFont'])
        menu.addSeparator()
        menu.addMenu(self.allActions['FormatFontSize'].parent())
        menu.addAction(self.allActions['FormatFontColor'])
        menu.addSeparator()
        menu.addAction(self.allActions['FormatExtLink'])
        menu.addAction(self.allActions['FormatIntLink'])
        menu.addSeparator()
        menu.addAction(self.allActions['FormatSelectAll'])
        menu.addAction(self.allActions['FormatClearFormat'])
        menu.addSeparator()
        menu.addAction(self.allActions['EditCut'])
        menu.addAction(self.allActions['EditCopy'])
        menu.addAction(self.allActions['EditPaste'])
        menu.addAction(self.allActions['EditPastePlain'])
        menu.exec_(event.globalPos())

    def mousePressEvent(self, event):
        """Handle ctrl + click to follow links.

        Arguments:
            event -- the mouse event
        """
        if (event.button() == Qt.LeftButton and
            event.modifiers() == Qt.ControlModifier):
            cursor = self.cursorForPosition(event.pos())
            address = cursor.charFormat().anchorHref()
            if address:
                if address.startswith('#'):
                    editView = self.parent().parent()
                    editView.selectModel.selectNodeById(address[1:])
                else:     # check for relative path
                    if urltools.isRelative(address):
                        defaultPath = (globalref.mainControl.
                                       defaultFilePath(True))
                        address = urltools.toAbsolute(address, defaultPath)
                    openExtUrl(address)
            event.accept()
        else:
            super().mousePressEvent(event)


class OneLineTextEditor(RichTextEditor):
    """An editor widget for single-line wysiwyg rich text fields.
    """
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)

    def insertFromMimeData(self, mimeSource):
        """Override to verify that only a single line is pasted or dropped.

        Arguments:
            mimeSource -- the mime source to be inserted
        """
        super().insertFromMimeData(mimeSource)
        text = self.contents()
        if '<br />' in text:
            text = text.split('<br />', 1)[0]
            self.blockSignals(True)
            self.setHtml(text)
            self.blockSignals(False)
            self.moveCursor(QTextCursor.End)

    def keyPressEvent(self, event):
        """Customize handling of return and control keys.

        Arguments:
            event -- the key press event
        """
        if event.key() not in (Qt.Key_Enter, Qt.Key_Return):
            super().keyPressEvent(event)


class LineEditor(QLineEdit):
    """An editor widget for unformatted single-line fields.

    Used both stand-alone and as part of the combo box editor.
    """
    dragLinkEnabled = False
    contentsChanged = pyqtSignal(QWidget)
    contextMenuPrep = pyqtSignal()
    def __init__(self, parent=None, subControl=False):
        """Initialize the editor class.

        Includes a colored triangle error flag for non-matching formats.
        Arguments:
            parent -- the parent, if given
            subcontrol -- true if used inside a combo box (no border or signal)
        """
        super().__init__(parent)
        self.setPalette(QApplication.palette())
        self.cursorPositionChanged.connect(self.updateActions)
        self.selectionChanged.connect(self.updateActions)
        try:
            self.allActions = parent.parent().allActions
        except AttributeError:  # view is a level up if embedded in a combo
            self.allActions = parent.parent().parent().allActions
        self.modified = False
        self.errorFlag = False
        self.savedCursorPos = None
        self.extraMenuActions = []
        if not subControl:
            self.setStyleSheet('QLineEdit {border: 2px solid '
                               'palette(highlight)}')
            self.textEdited.connect(self.signalUpdate)

    def setContents(self, text):
        """Set the contents of the editor to text.

        Arguments:
            text - the new text contents for the editor
        """
        self.setText(text)

    def contents(self):
        """Return the editor text contents.
        """
        return self.text()

    def signalUpdate(self):
        """Signal the delegate to update the model based on an editor change.
        """
        self.modified = True
        self.errorFlag = False
        self.contentsChanged.emit(self)

    def setErrorFlag(self):
        """Set the error flag to True and repaint the widget.
        """
        self.errorFlag = True
        self.update()

    def setCursorPoint(self, point):
        """Set the cursor to the given point.

        Arguments:
            point -- the QPoint for the new cursor position
        """
        self.savedCursorPos = self.cursorPositionAt(self.mapFromGlobal(point))
        self.setCursorPosition(self.savedCursorPos)

    def resetCursor(self):
        """Set the cursor to select all for tab-focus use.
        """
        self.selectAll()

    def paintEvent(self, event):
        """Add painting of the error flag to the paint event.
        
        Arguments:
            event -- the paint event
        """
        super().paintEvent(event)
        if self.errorFlag:
            painter = QPainter(self)
            path = QPainterPath(QPointF(0, 0))
            path.lineTo(0, 10)
            path.lineTo(10, 0)
            path.closeSubpath()
            painter.fillPath(path, QApplication.palette().highlight())

    def disableActions(self):
        """Reset action availability after focus is lost.
        """
        self.allActions['EditCut'].setEnabled(True)
        self.allActions['EditCopy'].setEnabled(True)
        mime = QApplication.clipboard().mimeData()
        self.allActions['EditPaste'].setEnabled(len(mime.data('text/xml') or
                                                    mime.data('text/plain'))
                                                > 0)

    def updateActions(self):
        """Set availability of context menu actions.
        """
        hasSelection = self.hasSelectedText()
        self.allActions['EditCut'].setEnabled(hasSelection)
        self.allActions['EditCopy'].setEnabled(hasSelection)
        mime = QApplication.clipboard().mimeData()
        self.allActions['EditPaste'].setEnabled(len(mime.data('text/plain'))
                                                > 0)

    def contextMenuEvent(self, event):
        """Override popup menu to add formatting actions.

        Arguments:
            event -- the menu event
        """
        self.contextMenuPrep.emit()
        menu = QMenu(self)
        if self.extraMenuActions:
            for action in self.extraMenuActions:
                menu.addAction(action)
            menu.addSeparator()
        menu.addAction(self.allActions['FormatSelectAll'])
        menu.addSeparator()
        menu.addAction(self.allActions['EditCut'])
        menu.addAction(self.allActions['EditCopy'])
        menu.addAction(self.allActions['EditPaste'])
        menu.exec_(event.globalPos())

    def focusInEvent(self, event):
        """Restore a saved cursor position for new editors.

        Arguments:
            event -- the focus event
        """
        super().focusInEvent(event)
        if (event.reason() == Qt.OtherFocusReason and
            self.savedCursorPos != None):
            self.setCursorPosition(self.savedCursorPos)
            self.savedCursorPos = None
        self.updateActions()

    def focusOutEvent(self, event):
        """Reset format actions on focus loss if not focusing a menu.

        Arguments:
            event -- the focus event
        """
        super().focusOutEvent(event)
        if event.reason() != Qt.PopupFocusReason:
            self.disableActions()

    def hideEvent(self, event):
        """Reset format actions when the editor is hidden.

        Arguments:
            event -- the hide event
        """
        self.disableActions()
        super().hideEvent(event)


class ReadOnlyEditor(LineEditor):
    """An editor widget that doesn't allow any edits.
    """
    def __init__(self, parent=None):
        """Initialize the editor class.

        Includes a colored triangle error flag for non-matching formats.
        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.setReadOnly(True)


class ComboEditor(QComboBox):
    """A general combo box editor widget.

    Uses the LineEditor class to paint the error flag.
    """
    dragLinkEnabled = False
    contentsChanged = pyqtSignal(QWidget)
    def __init__(self, parent=None):
        """Initialize the editor class.

        The self.fieldRef and self.nodeRef must be set after creation.
        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.setPalette(QApplication.palette())
        self.setStyleSheet('QComboBox {border: 2px solid palette(highlight)}')
        self.setEditable(True)
        self.setLineEdit(LineEditor(self, True))
        self.listView = QTreeWidget()
        self.listView.setColumnCount(2)
        self.listView.header().hide()
        self.listView.setRootIsDecorated(False)
        self.listView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.listView.header().setSectionResizeMode(QHeaderView.
                                                    ResizeToContents)
        self.setModel(self.listView.model())
        self.setView(self.listView)
        self.setModelColumn(0)
        # self.lineEdit().setFont(dataeditview.defaultFont)
        self.modified = False
        self.fieldRef = None
        self.nodeRef = None
        self.editTextChanged.connect(self.signalUpdate)

    def setContents(self, text):
        """Set the contents of the editor to text.

        Arguments:
            text - the new text contents for the editor
        """
        self.blockSignals(True)
        self.setEditText(text)
        self.blockSignals(False)

    def contents(self):
        """Return the editor text contents.
        """
        return self.currentText()

    def showPopup(self):
        """Load combo box with choices before showing it.
        """
        self.listView.setColumnCount(self.fieldRef.numChoiceColumns)
        text = self.currentText()
        if self.fieldRef.autoAddChoices:
            self.fieldRef.clearChoices()
            for node in self.nodeRef.modelRef.root.descendantGen():
                if node.formatName == self.nodeRef.formatName:
                    self.fieldRef.addChoice(node.data.get(self.fieldRef.name,
                                                          ''))
        self.blockSignals(True)
        self.clear()
        if self.fieldRef.numChoiceColumns == 1:
            choices = self.fieldRef.comboChoices()
            self.addItems(choices)
        else:
            annotatedChoices = self.fieldRef.annotatedComboChoices(text)
            for choice, annot in annotatedChoices:
                QTreeWidgetItem(self.listView, [choice, annot])
            choices = [choice for (choice, annot) in annotatedChoices]
        try:
            self.setCurrentIndex(choices.index(text))
        except ValueError:
            self.setEditText(text)
        self.blockSignals(False)
        super().showPopup()

    def signalUpdate(self):
        """Signal the delegate to update the model based on an editor change.
        """
        self.modified = True
        self.lineEdit().errorFlag = False
        self.contentsChanged.emit(self)

    def setErrorFlag(self):
        """Set the error flag to True and repaint the widget.
        """
        self.lineEdit().errorFlag = True
        self.update()

    def hasSelectedText(self):
        """Return True if text is selected.
        """
        return self.lineEdit().hasSelectedText()

    def selectAll(self):
        """Select all text in the line editor.
        """
        self.lineEdit().selectAll()

    def setCursorPoint(self, point):
        """Set the cursor to the given point.

        Arguments:
            point -- the QPoint for the new cursor position
        """
        self.lineEdit().setCursorPoint(point)

    def resetCursor(self):
        """Set the cursor to select all for tab-focus use.
        """
        self.lineEdit().selectAll()

    def copy(self):
        """Copy text selected in the line editor.
        """
        self.lineEdit().copy()

    def cut(self):
        """Cut text selected in the line editor.
        """
        self.lineEdit().cut()

    def paste(self):
        """Paste from the clipboard into the line editor.
        """
        self.lineEdit().paste()


class CombinationEditor(ComboEditor):
    """An editor widget for combination and auto-combination fields.

    Uses a combo box with a list of checkboxes in place of the list popup.
    """
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.checkBoxDialog = None

    def showPopup(self):
        """Override to show a popup entry widget in place of a list view.
        """
        if self.fieldRef.autoAddChoices:
            self.fieldRef.clearChoices()
            for node in self.nodeRef.modelRef.root.descendantGen():
                if node.formatName == self.nodeRef.formatName:
                    self.fieldRef.addChoice(node.data.get(self.fieldRef.name,
                                                          ''))
        selectList = self.fieldRef.comboActiveChoices(self.currentText())
        self.checkBoxDialog = CombinationDialog(self.fieldRef.comboChoices(),
                                                selectList, self)
        self.checkBoxDialog.setMinimumWidth(self.width())
        self.checkBoxDialog.buttonChanged.connect(self.updateText)
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

    def updateText(self):
        """Update the text based on a changed signal.
        """
        if self.checkBoxDialog:
            self.setEditText(self.fieldRef.joinText(self.checkBoxDialog.
                                                    selectList()))


class CombinationDialog(QDialog):
    """A popup dialog box for combination and auto-combination fields.
    """
    buttonChanged = pyqtSignal()
    def __init__(self, choiceList, selectList, parent=None):
        """Initialize the combination dialog.

        Arguments:
            choiceList -- a list of text choices
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
        selected = set(selectList)
        self.buttonGroup = QButtonGroup(self)
        self.buttonGroup.setExclusive(False)
        self.buttonGroup.buttonClicked.connect(self.buttonChanged)
        for text in choiceList:
            button = QCheckBox(text, innerWidget)
            if text in selected:
                button.setChecked(True)
            self.buttonGroup.addButton(button)
            innerLayout.addWidget(button)
        scrollArea.setWidget(innerWidget)
        buttons = self.buttonGroup.buttons()
        if buttons:
            buttons[0].setFocus()

    def selectList(self):
        """Return a list of currently checked text.
        """
        result = []
        for button in self.buttonGroup.buttons():
            if button.isChecked():
                result.append(button.text())
        return result


class DateEditor(ComboEditor):
    """An editor widget for date fields.

    Uses a combo box with a calendar widget in place of the list popup.
    """
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.calendar = None
        self.nowAction = QAction(_('Today\'s &Date'), self)
        self.nowAction.triggered.connect(self.setNow)
        self.lineEdit().extraMenuActions = [self.nowAction]

    def editorDate(self):
        """Return the date (as a QDate) set in the line editor.

        If none or invalid, return an invalid date.
        """
        try:
            dateStr = self.fieldRef.storedText(self.currentText())
        except ValueError:
            return QDate()
        return QDate.fromString(dateStr, Qt.ISODate)

    def showPopup(self):
        """Override to show a calendar widget in place of a list view.
        """
        if not self.calendar:
            self.calendar = QCalendarWidget(self)
            self.calendar.setWindowFlags(Qt.Popup)
            weekStart = optiondefaults.daysOfWeek.index(globalref.
                                                       genOptions['WeekStart'])
            self.calendar.setFirstDayOfWeek(weekStart + 1)
            self.calendar.setVerticalHeaderFormat(QCalendarWidget.
                                                  NoVerticalHeader)
            self.calendar.clicked.connect(self.setDate)
        date = self.editorDate()
        if date.isValid():
            self.calendar.setSelectedDate(date)
        self.calendar.show()
        pos = self.mapToGlobal(self.rect().bottomRight())
        pos.setX(pos.x() - self.calendar.width())
        screenBottom =  (QApplication.desktop().screenGeometry(self).
                         bottom())
        if pos.y() + self.calendar.height() > screenBottom:
            pos.setY(pos.y() - self.rect().height() - self.calendar.height())
        self.calendar.move(pos)

    def hidePopup(self):
        """Override to hide the calendar widget.
        """
        if self.calendar:
            self.calendar.hide()
        super().hidePopup()

    def setDate(self, date):
        """Set the date based on a signal from the calendar popup.

        Arguments:
            date -- the QDate to be set
        """
        dateStr = date.toString(Qt.ISODate)
        self.setEditText(self.fieldRef.formatEditorText(dateStr))
        self.calendar.hide()

    def setNow(self):
        """Set to today's date.
        """
        dateStr = QDate.currentDate().toString(Qt.ISODate)
        self.setEditText(self.fieldRef.formatEditorText(dateStr))


class TimeEditor(ComboEditor):
    """An editor widget for time fields.

    Only adds a now right-click menu action.
    """
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        nowAction = QAction(_('Set to &Now'), self)
        nowAction.triggered.connect(self.setNow)
        self.lineEdit().extraMenuActions = [nowAction]

    def setNow(self):
        """Set to the current time.
        """
        timeStr = QTime.currentTime().toString('hh:mm:ss.zzz')
        self.setEditText(self.fieldRef.formatEditorText(timeStr))


class DateTimeEditor(DateEditor):
    """An editor widget for DateTimeFields.

    Uses a combo box with a clandar widget in place of the list popup.
    """
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.nowAction.setText(_('Set to &Now'))

    def editorDate(self):
        """Return the date set in the line editor.

        If none or invalid, return an invalid date.
        """
        dateTime = self.editorDateTime()
        if dateTime.isValid():
            return dateTime.date()
        return QDate()

    def editorDateTime(self):
        """Return the datetime set in the line editor.

        If none or invalid, return an invalid date.
        """
        try:
            dateTimeStr = self.fieldRef.storedText(self.currentText())
        except ValueError:
            return QDateTime()
        return QDateTime.fromString(dateTimeStr[:-3],
                                    'yyyy-MM-dd HH:mm:ss.zzz')

    def setDate(self, date):
        """Set the date based on a signal from the calendar popup.

        Arguments:
            date -- the QDate to be set
        """
        dateTime = self.editorDateTime()
        dateTime.setDate(date)
        dateTimeStr = dateTime.toString('yyyy-MM-dd HH:mm:ss.zzz')
        self.setEditText(self.fieldRef.formatEditorText(dateTimeStr))
        self.calendar.hide()

    def setNow(self):
        """Set to the current date and time.
        """
        dateTime = QDateTime.currentDateTime()
        dateTimeStr = dateTime.toString('yyyy-MM-dd HH:mm:ss.zzz')
        self.setEditText(self.fieldRef.formatEditorText(dateTimeStr))


class ExtLinkEditor(ComboEditor):
    """An editor widget for external link fields.

    Uses a combo box with a link entry box in place of the list popup.
    """
    dragLinkEnabled = True
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.dialog = None
        openAction = QAction(_('&Open Link'), self)
        openAction.triggered.connect(self.openLink)
        folderAction = QAction(_('Open &Folder'), self)
        folderAction.triggered.connect(self.openFolder)
        self.lineEdit().extraMenuActions = [openAction, folderAction]
        self.lineEdit().contextMenuPrep.connect(self.updateActions)

    def showPopup(self):
        """Override to show a popup entry widget in place of a list view.
        """
        if not self.dialog:
            self.dialog = ExtLinkDialog(True, self)
            self.dialog.contentsChanged.connect(self.setLink)
        self.dialog.show()
        pos = self.mapToGlobal(self.rect().bottomRight())
        pos.setX(pos.x() - self.dialog.width() + 1)
        screenBottom =  (QApplication.desktop().screenGeometry(self).
                         bottom())
        if pos.y() + self.dialog.height() > screenBottom:
            pos.setY(pos.y() - self.rect().height() - self.dialog.height())
        self.dialog.move(pos)
        self.dialog.setFromEditor(self.currentText())

    def hidePopup(self):
        """Override to hide the popup entry widget.
        """
        if self.dialog:
            self.dialog.hide()
        super().hidePopup()

    def setLink(self):
        """Set the current link from the popup dialog.
        """
        self.setEditText(self.dialog.editorText())

    def openLink(self):
        """Open the link in a web browser.
        """
        text = self.currentText()
        if text:
            nameMatch = fieldformat.linkSeparateNameRegExp.match(text)
            if nameMatch:
                address = nameMatch.group(1).strip()
            else:
                address = text.strip()
            if address:
                if urltools.isRelative(address):
                    defaultPath = globalref.mainControl.defaultFilePath(True)
                    address = urltools.toAbsolute(address, defaultPath)
                openExtUrl(address)

    def openFolder(self):
        """Open the link in a file manager/explorer.
        """
        text = self.currentText()
        if text:
            nameMatch = fieldformat.linkSeparateNameRegExp.match(text)
            if nameMatch:
                address = nameMatch.group(1).strip()
            else:
                address = text.strip()
            if address and urltools.extractScheme(address) in ('', 'file'):
                if urltools.isRelative(address):
                    defaultPath = globalref.mainControl.defaultFilePath(True)
                    address = urltools.toAbsolute(address, defaultPath)
                address = os.path.dirname(address)
                openExtUrl(address)

    def updateActions(self):
        """Set availability of custom context menu actions.
        """
        address = self.currentText()
        if address:
            nameMatch = fieldformat.linkSeparateNameRegExp.match(address)
            if nameMatch:
                address = nameMatch.group(1).strip()
            else:
                address = address.strip()
        openAction, folderAction = self.lineEdit().extraMenuActions
        openAction.setEnabled(len(address) > 0)
        folderAction.setEnabled(len(address) > 0 and
                               urltools.extractScheme(address) in ('', 'file'))

    def addDroppedUrl(self, urlText):
        """Add the URL link that was dropped on this editor from the view.

        Arguments:
            urlText -- the text of the link
        """
        self.setEditText(urlText)

    def dragEnterEvent(self, event):
        """Accept drags of files to this widget.
        
        Arguments:
            event -- the drag event object
        """
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        """Open a file dropped onto this widget.
        
         Arguments:
             event -- the drop event object
        """
        fileList = event.mimeData().urls()
        if fileList:
            self.setEditText(fileList[0].toLocalFile())


_extLinkSchemes = ('http://', 'https://', 'mailto:', 'file://')
_extLinkSchemeDict = {proto.split(':', 1)[0]: proto for proto in
                        _extLinkSchemes}

class ExtLinkDialog(QDialog):
    """A popup or normal dialog box for external link editing.
    """
    contentsChanged = pyqtSignal()
    def __init__(self, popupDialog=False, parent=None):
        """Initialize the dialog widgets.

        Arguments:
            popupDialog -- add OK and cancel buttons if False
            parent -- the dialog's parent widget
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('External Link'))
        vertLayout = QVBoxLayout(self)
        vertLayout.setSpacing(1)
        schemeLabel = QLabel(_('Scheme'))
        vertLayout.addWidget(schemeLabel)
        schemeLayout = QHBoxLayout()
        vertLayout.addLayout(schemeLayout)
        schemeLayout.setSpacing(8)
        self.schemeButtons = QButtonGroup(self)
        self.schemeButtonDict = {}
        for scheme in _extLinkSchemes:
            scheme = scheme.split(':', 1)[0]
            button = QRadioButton(scheme)
            self.schemeButtons.addButton(button)
            self.schemeButtonDict[scheme] = button
            schemeLayout.addWidget(button)
        self.schemeButtonDict['http'].setChecked(True)
        self.schemeButtons.buttonClicked.connect(self.updateScheme)
        vertLayout.addSpacing(8)

        self.browseButton = QPushButton(_('&Browse for File'))
        self.browseButton.setAutoDefault(False)
        self.browseButton.clicked.connect(self.fileBrowse)
        vertLayout.addWidget(self.browseButton)
        vertLayout.addSpacing(8)

        self.pathTypeLabel = QLabel(_('File Path Type'))
        vertLayout.addWidget(self.pathTypeLabel)
        pathTypeLayout = QHBoxLayout()
        vertLayout.addLayout(pathTypeLayout)
        pathTypeLayout.setSpacing(8)
        pathTypeButtons = QButtonGroup(self)
        self.absoluteButton = QRadioButton(_('Absolute'))
        pathTypeButtons.addButton(self.absoluteButton)
        pathTypeLayout.addWidget(self.absoluteButton)
        self.relativeButton = QRadioButton(_('Relative'))
        pathTypeButtons.addButton(self.relativeButton)
        pathTypeLayout.addWidget(self.relativeButton)
        self.absoluteButton.setChecked(True)
        pathTypeButtons.buttonClicked.connect(self.updatePathType)
        vertLayout.addSpacing(8)

        addressLabel = QLabel(_('Address'))
        vertLayout.addWidget(addressLabel)
        self.addressEdit = QLineEdit()
        self.addressEdit.textEdited.connect(self.checkAddress)
        vertLayout.addWidget(self.addressEdit)
        vertLayout.addSpacing(8)

        nameLabel = QLabel(_('Display Name'))
        vertLayout.addWidget(nameLabel)
        self.nameEdit = QLineEdit()
        self.nameEdit.textEdited.connect(self.contentsChanged)
        vertLayout.addWidget(self.nameEdit)
        if popupDialog:
            self.setWindowFlags(Qt.Popup)
        else:
            vertLayout.addSpacing(8)
            ctrlLayout = QHBoxLayout()
            vertLayout.addLayout(ctrlLayout)
            ctrlLayout.addStretch(0)
            okButton = QPushButton(_('&OK'))
            ctrlLayout.addWidget(okButton)
            okButton.clicked.connect(self.accept)
            cancelButton = QPushButton(_('&Cancel'))
            ctrlLayout.addWidget(cancelButton)
            cancelButton.clicked.connect(self.reject)
        self.addressEdit.setFocus()

    def setFromEditor(self, editorText):
        """Set the dialog contents from a string in editor format.

        Arguments:
            editorText -- string in "link [name]" format
        """
        name = address = ''
        editorText = editorText.strip()
        if editorText:
            nameMatch = fieldformat.linkSeparateNameRegExp.match(editorText)
            if nameMatch:
                address, name = nameMatch.groups()
                address = address.strip()
            else:
                address = editorText
                name = urltools.shortName(address)
        self.setFromComponents(address, name)

    def setFromHtml(self, htmlStr):
        """Set the dialog contents from an HTML link.

        Arguments:
            htmlStr -- string in HTML link format
        """
        name = address = ''
        if htmlStr:
            linkMatch = fieldformat.linkRegExp.search(htmlStr)
            if linkMatch:
                address, name = linkMatch.groups()
                name = name.strip()
                if not name:
                    name = urltools.shortName(address)
        self.setFromComponents(address, name)

    def setFromComponents(self, address, name):
        """Set the dialog contents from separate address and name.

        Arguments:
            address -- the link address, including the scheme prefix
            name -- the displayed name for the link
        """
        scheme = urltools.extractScheme(address)
        if scheme not in _extLinkSchemeDict:
            if not scheme:
                address = urltools.replaceScheme('file', address)
            scheme = 'file'
        self.schemeButtonDict[scheme].setChecked(True)
        if address and urltools.isRelative(address):
            self.relativeButton.setChecked(True)
        else:
            self.absoluteButton.setChecked(True)
        self.addressEdit.setText(address)
        self.nameEdit.setText(name)
        self.updateFileControls()

    def editorText(self):
        """Return the dialog contents in data editor format ("link [name]").
        """
        address = self.currentAddress()
        if not address:
            return ''
        name = self.nameEdit.text().strip()
        if not name:
            return address
        return '{0} [{1}]'.format(address, name)

    def htmlText(self):
        """Return the dialog contents in HTML link format.
        """
        address = self.currentAddress()
        if not address:
            return ''
        name = self.nameEdit.text().strip()
        if not name:
            name = urltools.shortName(address)
        return '<a href="{0}">{1}</a>'.format(address, name)

    def currentAddress(self):
        """Return current address with the selected scheme prefix.
        """
        scheme = self.schemeButtons.checkedButton().text()
        address = self.addressEdit.text().strip()
        return urltools.replaceScheme(scheme, address)

    def checkAddress(self):
        """Update controls based on a change to the address field.

        Makes minimum changes to scheme and absolute controls,
        since the address may be incomplete.
        """
        address = self.addressEdit.text().strip()
        scheme = urltools.extractScheme(address)
        if scheme in _extLinkSchemeDict:
            self.schemeButtonDict[scheme].setChecked(True)
            if scheme != 'file':
                self.absoluteButton.setChecked(True)
        self.updateFileControls()
        self.contentsChanged.emit()

    def updateScheme(self):
        """Update scheme in the address due to scheme button change.
        """
        scheme = self.schemeButtons.checkedButton().text()
        address = self.addressEdit.text().strip()
        address = urltools.replaceScheme(scheme, address)
        self.addressEdit.setText(address)
        if urltools.isRelative(address):
            self.relativeButton.setChecked(True)
        else:
            self.absoluteButton.setChecked(True)
        self.updateFileControls()
        self.contentsChanged.emit()

    def updatePathType(self):
        """Update file path based on a change in the absolute/relative control.
        """
        absolute = self.absoluteButton.isChecked()
        defaultPath = globalref.mainControl.defaultFilePath(True)
        address = self.addressEdit.text().strip()
        if absolute:
            address = urltools.toAbsolute(address, defaultPath)
        else:
            address = urltools.toRelative(address, defaultPath)
        self.addressEdit.setText(address)
        self.contentsChanged.emit()

    def updateFileControls(self):
        """Set file browse & type controls available based on current scheme.
        """
        enable = self.schemeButtons.checkedButton().text() == 'file'
        self.browseButton.setEnabled(enable)
        self.pathTypeLabel.setEnabled(enable)
        self.absoluteButton.setEnabled(enable)
        self.relativeButton.setEnabled(enable)

    def fileBrowse(self):
        """Show dialog to browse for a file to be linked.

        Adjust based on absolute or relative path settings.
        """
        refPath = globalref.mainControl.defaultFilePath(True)
        defaultPath = refPath
        oldAddress = self.addressEdit.text().strip()
        oldScheme = urltools.extractScheme(oldAddress)
        if oldAddress and not oldScheme or oldScheme == 'file':
            if urltools.isRelative(oldAddress):
                oldAddress = urltools.toAbsolute(oldAddress, refPath)
            oldAddress = urltools.extractAddress(oldAddress)
            if os.access(oldAddress, os.F_OK):
                defaultPath = oldAddress
        address, selFltr = QFileDialog.getOpenFileName(self,
                                            _('TreeLine - External Link File'),
                                            defaultPath,
                                            globalref.fileFilters['all'])
        if address:
            if self.relativeButton.isChecked():
                address = urltools.toRelative(address, refPath)
            self.setFromComponents(address, urltools.shortName(address))
        self.show()
        self.contentsChanged.emit()


class IntLinkEditor(ComboEditor):
    """An editor widget for internal link fields.

    Uses a combo box with a link entry box in place of the list popup.
    """
    inLinkSelectMode = pyqtSignal(bool)
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.intLinkDialog = None
        self.addedIntLinkFlag = False
        openAction = QAction(_('&Go to Target'), self)
        openAction.triggered.connect(self.openLink)
        self.lineEdit().extraMenuActions = [openAction]

    def showPopup(self):
        """Override to show a popup entry widget in place of a list view.
        """
        if not self.intLinkDialog:
            self.intLinkDialog = IntLinkDialog(True, self)
            self.intLinkDialog.contentsChanged.connect(self.setLink)
        self.intLinkDialog.show()
        pos = self.mapToGlobal(self.rect().bottomRight())
        pos.setX(pos.x() - self.intLinkDialog.width() + 1)
        screenBottom =  (QApplication.desktop().screenGeometry(self).
                         bottom())
        if pos.y() + self.intLinkDialog.height() > screenBottom:
            pos.setY(pos.y() - self.rect().height() -
                     self.intLinkDialog.height())
        self.intLinkDialog.move(pos)
        self.intLinkDialog.setFromEditor(self.currentText())

    def hidePopup(self):
        """Override to hide the popup entry widget.
        """
        if self.intLinkDialog:
            if self.intLinkDialog.targetButton.isChecked():
                self.intLinkDialog.toggleTargetClick(False)
            self.intLinkDialog.hide()
        super().hidePopup()

    def signalUpdate(self):
        """Signal the delegate to update the model based on an editor change.

        Also checks for invalid link destination.
        """
        self.modified = True
        self.lineEdit().errorFlag = False
        text = self.currentText()
        if text:
            nameMatch = fieldformat.linkSeparateNameRegExp.match(text)
            if nameMatch:
                address = nameMatch.group(1).strip()
            else:
                address = text.strip()
            if address:
                self.addedIntLinkFlag = True
                editView = self.parent().parent()
                if address not in editView.selectModel.model().nodeIdDict:
                    self.lineEdit().errorFlag = True
        self.contentsChanged.emit(self)

    def setLink(self):
        """Set the current link from the popup dialog.
        """
        self.setEditText(self.intLinkDialog.editorText())

    def setLinkFromNode(self, node):
        """Set the current link from a clicked node.

        Arguments:
            node -- the node to set the unique ID from
        """
        if self.intLinkDialog:
            self.intLinkDialog.setFromNode(node)
        self.setLink()

    def openLink(self):
        """Open the link in a web browser.
        """
        text = self.currentText()
        if text:
            nameMatch = fieldformat.linkSeparateNameRegExp.match(text)
            if nameMatch:
                address = nameMatch.group(1).strip()
                if address:
                    editView = self.parent().parent()
                    editView.selectModel.selectNodeById(address)


_targetButtonLabel = {False: _('Enable click-on-&target'),
                      True: _('Disable click-on-&target')}

class IntLinkDialog(QDialog):
    """A popup or normal dialog box for internal link editing.
    """
    contentsChanged = pyqtSignal()
    targetClickDialogRef = None
    def __init__(self, popupDialog=False, parent=None):
        """Initialize the dialog widgets.

        Arguments:
            popupDialog -- add OK and cancel buttons if False
            parent -- the dialog's parent widget
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Internal Link'))
        self.popupDialog = popupDialog
        self.targetMode = False
        vertLayout = QVBoxLayout(self)
        vertLayout.setSpacing(1)
        self.targetButton = QPushButton(_targetButtonLabel[False])
        self.targetButton.setCheckable(True)
        self.targetButton.clicked.connect(self.toggleTargetClick)
        vertLayout.addWidget(self.targetButton)
        vertLayout.addSpacing(8)
        addressLabel = QLabel(_('Unique ID'))
        vertLayout.addWidget(addressLabel)
        self.addressEdit = QLineEdit()
        self.addressEdit.textEdited.connect(self.contentsChanged)
        vertLayout.addWidget(self.addressEdit)
        vertLayout.addSpacing(8)
        nameLabel = QLabel(_('Display Name'))
        vertLayout.addWidget(nameLabel)
        self.nameEdit = QLineEdit()
        self.nameEdit.textEdited.connect(self.contentsChanged)
        vertLayout.addWidget(self.nameEdit)
        if self.popupDialog:
            self.setWindowFlags(Qt.Popup)
        else:
            vertLayout.addSpacing(8)
            ctrlLayout = QHBoxLayout()
            vertLayout.addLayout(ctrlLayout)
            ctrlLayout.addStretch(0)
            okButton = QPushButton(_('&OK'))
            ctrlLayout.addWidget(okButton)
            okButton.setDefault(True)
            okButton.clicked.connect(self.accept)
            cancelButton = QPushButton(_('&Cancel'))
            ctrlLayout.addWidget(cancelButton)
            cancelButton.clicked.connect(self.reject)

    def setFromEditor(self, editorText):
        """Set the dialog contents from a string in editor format.

        Arguments:
            editorText -- string in "link [name]" format
        """
        name = address = ''
        if editorText:
            nameMatch = fieldformat.linkSeparateNameRegExp.match(editorText)
            if nameMatch:
                address, name = nameMatch.groups()
            else:
                name = address = editorText
            address = address.strip()
        self.setFromComponents(address, name)

    def setFromHtml(self, htmlStr):
        """Set the dialog contents from an HTML link.

        Arguments:
            htmlStr -- string in HTML link format
        """
        name = address = ''
        if htmlStr:
            linkMatch = fieldformat.linkRegExp.search(htmlStr)
            if linkMatch:
                address, name = linkMatch.groups()
                address = address.lstrip('#')
                name = name.strip()
                if not name:
                    name = address
        self.setFromComponents(address, name)

    def setFromNode(self, node):
        """Set the dialog contents from a clicked node.

        Arguments:
            node -- the node to set the unique ID from
        """
        if self.targetMode:
            address = node.uniqueId
            name = self.nameEdit.text().strip()
            if not name:
                name = node.title()
            self.setFromComponents(address, name)
            self.toggleTargetClick(False)

    def setFromComponents(self, address, name):
        """Set the dialog contents from separate address and name.

        Arguments:
            address -- the link address, including the protocol prefix
            name -- the displayed name for the link
        """
        self.addressEdit.setText(address)
        self.nameEdit.setText(name)

    def editorText(self):
        """Return the dialog contents in data editor format ("link [name]").
        """
        address = self.addressEdit.text().strip()
        name = self.nameEdit.text().strip()
        if not name:
            return address
        return '{0} [{1}]'.format(address, name)

    def htmlText(self):
        """Return the dialog contents in HTML link format.
        """
        address = self.addressEdit.text().strip()
        name = self.nameEdit.text().strip()
        if not name:
            name = address
        return '<a href="#{0}">{1}</a>'.format(address, name)

    def address(self):
        """Return the address from the dialog contents.
        """
        return  self.addressEdit.text().strip()

    def toggleTargetClick(self, enabled):
        """Toggle state of clicking on target nodes.

        Arguments:
            enabled -- True if clicking enabled
        """
        self.targetMode = enabled
        self.targetButton.setChecked(enabled)
        self.targetButton.setText(_targetButtonLabel[enabled])
        self.addressEdit.setEnabled(not enabled)
        if self.popupDialog:
            if enabled:
                self.setWindowFlags(Qt.Dialog |
                                    Qt.FramelessWindowHint)
                if (IntLinkDialog.targetClickDialogRef and
                    IntLinkDialog.targetClickDialogRef != self):
                    IntLinkDialog.targetClickDialogRef.parent().hidePopup()
                IntLinkDialog.targetClickDialogRef = self
            else:
                self.setWindowFlags(Qt.Popup)
                IntLinkDialog.targetClickDialogRef = None
        else:
            self.setModal(not enabled)
        self.show()
        self.parent().inLinkSelectMode.emit(enabled)

    def accept(self):
        """Reset target click mode if necessary after the user clicks OK.
        """
        if self.targetMode:
            self.toggleTargetClick(False)
        super().accept()

    def reject(self):
        """Reset target click mode if necessary after the user cancels.
        """
        if self.targetMode:
            self.toggleTargetClick(False)
        super().reject()


class PictureLinkEditor(ComboEditor):
    """An editor widget for picture link fields.

    Uses a combo box with a link entry box in place of the list popup.
    """
    dragLinkEnabled = True
    def __init__(self, parent=None):
        """Initialize the editor class.

        Arguments:
            parent -- the parent, if given
        """
        super().__init__(parent)
        self.dialog = None
        openAction = QAction(_('&Open Picture'), self)
        openAction.triggered.connect(self.openPicture)
        self.lineEdit().extraMenuActions = [openAction]

    def showPopup(self):
        """Override to show a popup entry widget in place of a list view.
        """
        if not self.dialog:
            self.dialog = PictureLinkDialog(True, self)
            self.dialog.contentsChanged.connect(self.setLink)
        self.dialog.show()
        pos = self.mapToGlobal(self.rect().bottomRight())
        pos.setX(pos.x() - self.dialog.width() + 1)
        screenBottom =  (QApplication.desktop().screenGeometry(self).
                         bottom())
        if pos.y() + self.dialog.height() > screenBottom:
            pos.setY(pos.y() - self.rect().height() - self.dialog.height())
        self.dialog.move(pos)
        self.dialog.setAddress(self.currentText())

    def hidePopup(self):
        """Override to hide the popup entry widget.
        """
        if self.dialog:
            self.dialog.hide()
        super().hidePopup()

    def setLink(self):
        """Set the current link from the popup dialog.
        """
        self.setEditText(self.dialog.currentAddress())

    def openPicture(self):
        """Open the link in a web browser.
        """
        address = self.currentText()
        if address:
            if urltools.isRelative(address):
                defaultPath = globalref.mainControl.defaultFilePath(True)
                address = urltools.toAbsolute(address, defaultPath)
            openExtUrl(address)

    def addDroppedUrl(self, urlText):
        """Add the URL link that was dropped on this editor from the view.

        Arguments:
            urlText -- the text of the link
        """
        self.setEditText(urlText)


class PictureLinkDialog(QDialog):
    """A popup or normal dialog box for picture link editing.
    """
    thumbnailSize = QSize(250, 100)
    contentsChanged = pyqtSignal()
    def __init__(self, popupDialog=False, parent=None):
        """Initialize the dialog widgets.

        Arguments:
            popupDialog -- add OK and cancel buttons if False
            parent -- the dialog's parent widget
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint |
                            Qt.WindowCloseButtonHint)
        self.setWindowTitle(_('Picture Link'))
        self.setMinimumWidth(self.thumbnailSize.width())
        vertLayout = QVBoxLayout(self)
        vertLayout.setSpacing(1)
        self.thumbnail = QLabel()
        pixmap = QPixmap(self.thumbnailSize)
        pixmap.fill()
        self.thumbnail.setPixmap(pixmap)
        vertLayout.addWidget(self.thumbnail, 0, Qt.AlignHCenter)
        vertLayout.addSpacing(8)

        self.browseButton = QPushButton(_('&Browse for File'))
        self.browseButton.setAutoDefault(False)
        self.browseButton.clicked.connect(self.fileBrowse)
        vertLayout.addWidget(self.browseButton)
        vertLayout.addSpacing(8)

        self.pathTypeLabel = QLabel(_('File Path Type'))
        vertLayout.addWidget(self.pathTypeLabel)
        pathTypeLayout = QHBoxLayout()
        vertLayout.addLayout(pathTypeLayout)
        pathTypeLayout.setSpacing(8)
        pathTypeButtons = QButtonGroup(self)
        self.absoluteButton = QRadioButton(_('Absolute'))
        pathTypeButtons.addButton(self.absoluteButton)
        pathTypeLayout.addWidget(self.absoluteButton)
        self.relativeButton = QRadioButton(_('Relative'))
        pathTypeButtons.addButton(self.relativeButton)
        pathTypeLayout.addWidget(self.relativeButton)
        self.absoluteButton.setChecked(True)
        pathTypeButtons.buttonClicked.connect(self.updatePathType)
        vertLayout.addSpacing(8)

        addressLabel = QLabel(_('Address'))
        vertLayout.addWidget(addressLabel)
        self.addressEdit = QLineEdit()
        self.addressEdit.textEdited.connect(self.checkAddress)
        vertLayout.addWidget(self.addressEdit)
        vertLayout.addSpacing(8)

        if popupDialog:
            self.setWindowFlags(Qt.Popup)
        else:
            vertLayout.addSpacing(8)
            ctrlLayout = QHBoxLayout()
            vertLayout.addLayout(ctrlLayout)
            ctrlLayout.addStretch(0)
            okButton = QPushButton(_('&OK'))
            ctrlLayout.addWidget(okButton)
            okButton.clicked.connect(self.accept)
            cancelButton = QPushButton(_('&Cancel'))
            ctrlLayout.addWidget(cancelButton)
            cancelButton.clicked.connect(self.reject)
        self.addressEdit.setFocus()

    def setAddress(self, address):
        """Set the dialog contents from a string in editor format.

        Arguments:
            address -- URL string for the address
        """
        if address and urltools.isRelative(address):
            self.relativeButton.setChecked(True)
        else:
            self.absoluteButton.setChecked(True)
        self.addressEdit.setText(address)
        self.updateThumbnail()

    def setFromHtml(self, htmlStr):
        """Set the dialog contents from an HTML link.

        Arguments:
            htmlStr -- string in HTML link format
        """
        linkMatch = imageRegExp.search(htmlStr)
        if linkMatch:
            address = linkMatch.group(1)
        self.setAddress(address.strip())

    def htmlText(self):
        """Return the dialog contents in HTML link format.
        """
        address = self.currentAddress()
        if not address:
            return ''
        return '<img src="{0}" />'.format(address)

    def currentAddress(self):
        """Return current address with the selected scheme prefix.
        """
        return self.addressEdit.text().strip()

    def checkAddress(self):
        """Update absolute controls based on a change to the address field.
        """
        address = self.addressEdit.text().strip()
        if address:
            if urltools.isRelative(address):
                self.relativeButton.setChecked(True)
            else:
                self.absoluteButton.setChecked(True)
        self.updateThumbnail()
        self.contentsChanged.emit()

    def updatePathType(self):
        """Update path based on a change in the absolute/relative control.
        """
        absolute = self.absoluteButton.isChecked()
        defaultPath = globalref.mainControl.defaultFilePath(True)
        address = self.addressEdit.text().strip()
        if absolute:
            address = urltools.toAbsolute(address, defaultPath, False)
        else:
            address = urltools.toRelative(address, defaultPath)
        self.addressEdit.setText(address)
        self.updateThumbnail()
        self.contentsChanged.emit()

    def updateThumbnail(self):
        """Update the thumbnail with an image from the current address.
        """
        address = self.addressEdit.text().strip()
        if urltools.isRelative(address):
            refPath = globalref.mainControl.defaultFilePath(True)
            address = urltools.toAbsolute(address, refPath, False)
        pixmap = QPixmap(address)
        if pixmap.isNull():
            pixmap = QPixmap(self.thumbnailSize)
            pixmap.fill()
        else:
            pixmap = pixmap.scaled(self.thumbnailSize,
                                   Qt.KeepAspectRatio)
        self.thumbnail.setPixmap(pixmap)

    def fileBrowse(self):
        """Show dialog to browse for a file to be linked.

        Adjust based on absolute or relative path settings.
        """
        refPath = globalref.mainControl.defaultFilePath(True)
        defaultPath = refPath
        oldAddress = self.addressEdit.text().strip()
        if oldAddress:
            if urltools.isRelative(oldAddress):
                oldAddress = urltools.toAbsolute(oldAddress, refPath)
            oldAddress = urltools.extractAddress(oldAddress)
            if os.access(oldAddress, os.F_OK):
                defaultPath = oldAddress
        address, selFltr = QFileDialog.getOpenFileName(self,
                                                  _('TreeLine - Picture File'),
                                                  defaultPath,
                                                  globalref.fileFilters['all'])
        if address:
            if self.relativeButton.isChecked():
                address = urltools.toRelative(address, refPath)
            self.setAddress(address)
        self.updateThumbnail()
        self.show()
        self.contentsChanged.emit()


    ####  Utility Functions  ####

def openExtUrl(path):
    """Open a web browser or a application for a directory or file.

    Arguments:
        path -- the path to open
    """
    if sys.platform.startswith('win'):
        os.startfile(path)
    elif sys.platform.startswith('darwin'):
        subprocess.call(['open', path])
    else:
        subprocess.call(['xdg-open', path])
