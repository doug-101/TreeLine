#!/usr/bin/env python3

#******************************************************************************
# printdata.py, provides a class for printing
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import os.path
import enum
from PyQt5.QtCore import QMarginsF, QSizeF, Qt
from PyQt5.QtGui import (QAbstractTextDocumentLayout, QFontMetrics,
                         QPageLayout, QPageSize, QPainter, QTextDocument)
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
import treeoutput
import printdialogs
import globalref

PrintScope = enum.IntEnum('PrintScope', 'entireTree selectBranch selectNode')
_defaultMargin = 0.5
_defaultHeaderPos = 0.2
_defaultColumnSpace = 0.5


class PrintData:
    """Class to handle printing of tree output data.
    
    Stores print data and main printing functions.
    """
    def __init__(self, localControl):
        """Initialize the print data.

        Arguments:
            localControl -- a reference to the parent local control
        """
        self.localControl = localControl
        self.outputGroup = None
        self.printWhat = PrintScope.entireTree
        self.includeRoot = True
        self.openOnly = False
        self.printer = QPrinter(QPrinter.HighResolution)
        self.pageLayout = self.printer.pageLayout()
        self.setDefaults()
        self.adjustSpacing()

    def setDefaults(self):
        """Set all paparmeters saved in TreeLine files to default values.
        """
        self.drawLines = True
        self.widowControl = True
        self.indentFactor = 2.0
        self.pageLayout.setUnits(QPageLayout.Inch)
        self.pageLayout.setPageSize(QPageSize(QPageSize.Letter))
        self.pageLayout.setOrientation(QPageLayout.Portrait)
        self.pageLayout.setMargins(QMarginsF(*(_defaultMargin,) * 4))
        self.headerMargin = _defaultHeaderPos
        self.footerMargin = _defaultHeaderPos
        self.numColumns = 1
        self.columnSpacing = _defaultColumnSpace
        self.headerText = ''
        self.footerText = ''
        self.useDefaultFont = True
        self.setDefaultFont()

    def setDefaultFont(self):
        """Set the default font initially and based on an output font change.
        """
        self.defaultFont = QTextDocument().defaultFont()
        fontName = globalref.miscOptions['OutputFont']
        if fontName:
            self.defaultFont.fromString(fontName)
        if self.useDefaultFont:
            self.mainFont = self.defaultFont

    def adjustSpacing(self):
        """Adjust line spacing & indent size based on font & indent factor.
        """
        self.lineSpacing = QFontMetrics(self.mainFont,
                                        self.printer).lineSpacing()
        self.indentSize = self.indentFactor * self.lineSpacing

    def fileData(self):
        """Return a dictionary of non-default settings for storage.
        """
        data = {}
        if not self.drawLines:
            data['printlines'] = False
        if not self.widowControl:
            data['printwidowcontrol'] = False
        if self.indentFactor != 2.0:
            data['printindentfactor'] = self.indentFactor
        pageSizeId = self.pageLayout.pageSize().id()
        if pageSizeId == QPageSize.Custom:
            paperWidth, paperHeight = self.roundedPaperSize()
            data['printpaperwidth'] = paperWidth
            data['printpaperheight'] = paperHeight
        elif pageSizeId != QPageSize.Letter:
            data['printpapersize'] = self.paperSizeName(pageSizeId)
        if self.pageLayout.orientation() != QPageLayout.Portrait:
            data['printportrait'] = False
        if self.roundedMargins() != (_defaultMargin,) * 4:
            data['printmargins'] = list(self.roundedMargins())
        if self.headerMargin != _defaultHeaderPos:
            data['printheadermargin'] = self.headerMargin
        if self.footerMargin != _defaultHeaderPos:
            data['printfootermargin'] = self.footerMargin
        if self.numColumns > 1:
            data['printnumcolumns'] = self.numColumns
        if self.columnSpacing != _defaultColumnSpace:
            data['printcolumnspace'] = self.columnSpacing
        if self.headerText:
            data['printheadertext'] = self.headerText
        if self.footerText:
            data['printfootertext'] = self.footerText
        if not self.useDefaultFont:
            data['printfont'] = self.mainFont.toString()
        return data

    def readData(self, data):
        """Restore saved settings from a dictionary.

        Arguments:
            data -- a dictionary of stored non-default settings
        """
        self.setDefaults()   # necessary for undo/redo
        self.drawLines = data.get('printlines', True)
        self.widowControl = data.get('printwidowcontrol', True)
        self.indentFactor = data.get('printindentfactor', 2.0)
        if 'printpapersize' in data:
            self.pageLayout.setPageSize(QPageSize(getattr(QPageSize,
                                                  data['printpapersize'])))
            self.pageLayout.setMargins(QMarginsF(*(_defaultMargin,) * 4))
        if 'printpaperwidth' in data and 'printpaperheight' in data:
            width =  data['printpaperwidth']
            height = data['printpaperheight']
            self.pageLayout.setPageSize(QPageSize(QSizeF(width, height),
                                        QPageSize.Inch))
            self.pageLayout.setMargins(QMarginsF(*(_defaultMargin,) * 4))
        if not data.get('printportrait', True):
            self.pageLayout.setOrientation(QPageLayout.Landscape)
        if 'printmargins' in data:
            margins = data['printmargins']
            self.pageLayout.setMargins(QMarginsF(*margins))
        self.headerMargin = data.get('printheadermargin', _defaultHeaderPos)
        self.footerMargin = data.get('printfootermargin', _defaultHeaderPos)
        self.numColumns = data.get('printnumcolumns', 1)
        self.columnSpacing = data.get('printcolumnspace', _defaultColumnSpace)
        self.headerText = data.get('printheadertext', '')
        self.footerText = data.get('printfootertext', '')
        if 'printfont' in data:
            self.useDefaultFont = False
            self.mainFont.fromString(data['printfont'])
        self.adjustSpacing()

    def roundedMargins(self):
        """Return a tuple of rounded page margins in inches.

        Rounds to nearest .01" to avoid Qt unit conversion artifacts.
        """
        margins = self.pageLayout.margins(QPageLayout.Inch)
        return tuple(round(margin, 2) for margin in
                     (margins.left(), margins.top(), margins.right(),
                      margins.bottom()))

    def roundedPaperSize(self):
        """Return a tuple of rounded paper width and height.

        Rounds to nearest .01" to avoid Qt unit conversion artifacts.
        """
        size = self.pageLayout.fullRect(QPageLayout.Inch)
        return (round(size.width(), 2), round(size.height(), 2))

    def paperSizeName(self, sizeId=None):
        """Return a QPageSize attribute name matching the paper size ID.

        Arguments:
            sizeId -- the Qt size ID, if None, use current size
        """
        if sizeId == None:
            sizeId = self.pageLayout.pageSize().id()
        matches = []
        for name, num in vars(QPageSize).items():
            if num == sizeId:
                matches.append(name)
        if not matches:
            return 'Custom'
        if len(matches) > 1:
            text = QPageSize(sizeId).name().split(None, 1)[0]
            for name in matches:
                if name == text:
                    return name
        return matches[0]

    def setupData(self):
        """Load data to be printed and set page info.
        """
        if self.printWhat == PrintScope.entireTree:
            selSpots = self.localControl.structure.rootSpots()
        else:
            selSpots = (self.localControl.currentSelectionModel().
                        selectedSpots())
            if not selSpots:
                selSpots = self.localControl.structure.rootSpots()
        self.outputGroup = treeoutput.OutputGroup(selSpots, self.includeRoot,
                                                  self.printWhat !=
                                                  PrintScope.selectNode,
                                                  self.openOnly)
        self.paginate()

    def paginate(self):
        """Define the pages and locations of output items and set page range.
        """
        pageNum = 1
        columnNum = 0
        pagePos = 0
        itemSplit = False
        self.checkPageLayout()
        heightAvail = (self.pageLayout.paintRect().height() *
                       self.printer.logicalDpiY())
        columnSpacing = int(self.columnSpacing * self.printer.logicalDpiX())
        widthAvail = ((self.pageLayout.paintRect().width() *
                       self.printer.logicalDpiX() -
                       columnSpacing * (self.numColumns - 1)) //
                      self.numColumns)
        newGroup = treeoutput.OutputGroup([])
        while self.outputGroup:
            item = self.outputGroup.pop(0)
            widthRemain = widthAvail - item.level * self.indentSize
            if pagePos != 0 and (newGroup[-1].addSpace or item.addSpace):
                pagePos += self.lineSpacing
            if item.siblingPrefix:
                siblings = treeoutput.OutputGroup([])
                siblings.append(item)
                while True:
                    item = siblings.combineLines()
                    item.setDocHeight(self.printer, widthRemain, self.mainFont,
                                      True)
                    if pagePos + item.height > heightAvail:
                        self.outputGroup.insert(0, siblings.pop())
                        item = (siblings.combineLines() if siblings else
                                None)
                        break
                    if (self.outputGroup and
                        item.level == self.outputGroup[0].level and
                        item.equalPrefix(self.outputGroup[0])):
                        siblings.append(self.outputGroup.pop(0))
                    else:
                        break
            if item:
                item.setDocHeight(self.printer, widthRemain, self.mainFont,
                                  True)
                if item.height > heightAvail and not itemSplit:
                    item, newItem = item.splitDocHeight(heightAvail - pagePos,
                                                        heightAvail,
                                                        self.printer,
                                                        widthRemain,
                                                        self.mainFont)
                    if newItem:
                        self.outputGroup.insert(0, newItem)
                        itemSplit = True
            if item and (pagePos + item.height <= heightAvail or pagePos == 0):
                item.pageNum = pageNum
                item.columnNum = columnNum
                item.pagePos = pagePos
                newGroup.append(item)
                pagePos += item.height
            else:
                if columnNum + 1 < self.numColumns:
                    columnNum += 1
                else:
                    pageNum += 1
                    columnNum = 0
                pagePos = 0
                itemSplit = False
                if item:
                    self.outputGroup.insert(0, item)
                    if self.widowControl and not item.siblingPrefix:
                        moveItems = []
                        moveHeight = 0
                        level = item.level
                        while (newGroup and not newGroup[-1].siblingPrefix and
                               newGroup[-1].level == level - 1 and
                               ((newGroup[-1].pageNum == pageNum - 1 and
                                 newGroup[-1].columnNum == columnNum) or
                                (newGroup[-1].pageNum == pageNum and
                                newGroup[-1].columnNum == columnNum - 1))):
                            moveItems.insert(0, newGroup.pop())
                            moveHeight += moveItems[0].height
                            level -= 1
                        if (moveItems and newGroup and
                            moveHeight < (heightAvail // 5)):
                            self.outputGroup[0:0] = moveItems
                        else:
                            newGroup.extend(moveItems)
        self.outputGroup = newGroup
        self.outputGroup.loadFamilyRefs()
        self.printer.setFromTo(1, pageNum)

    def checkPageLayout(self):
        """Check and set the page layout on the current printer.

        Verify that the layout settings match the printer, adjust if required.
        """
        if not self.printer.setPageLayout(self.pageLayout):
            tempPrinter = QPrinter()
            tempPageLayout = tempPrinter.pageLayout()
            tempPageLayout.setUnits(QPageLayout.Inch)
            pageSizeIssue = False
            defaultPageSize = tempPageLayout.pageSize()
            tempPageLayout.setPageSize(self.pageLayout.pageSize())
            if not tempPrinter.setPageLayout(tempPageLayout):
                pageSizeIssue = True
                tempPageLayout.setPageSize(defaultPageSize)
            marginIssue = not (tempPageLayout.setMargins(self.pageLayout.
                                                         margins()) and
                               tempPrinter.setPageLayout(tempPageLayout))
            if marginIssue:
                margin = 0.1
                while True:
                    if (tempPageLayout.setMargins(QMarginsF(*(margin,) * 4))
                        and tempPrinter.setPageLayout(tempPageLayout)):
                        break
                    margin += 0.1
                newMargins = []
                for oldMargin in self.roundedMargins():
                    newMargins.append(oldMargin if oldMargin >= margin else
                                      margin)
                tempPageLayout.setMargins(QMarginsF(*newMargins))
            tempPageLayout.setOrientation(self.pageLayout.orientation())
            self.printer.setPageLayout(tempPageLayout)
            if not pageSizeIssue and not marginIssue:
                return
            if pageSizeIssue and marginIssue:
                msg = _('Warning: Page size and margin settings unsupported '
                        'on current printer.\nSave page adjustments?')
            elif pageSizeIssue:
                msg = _('Warning: Page size setting unsupported '
                        'on current printer.\nSave adjustment?')
            else:
                msg = _('Warning: Margin settings unsupported '
                        'on current printer.\nSave adjustments?')
            ans = QMessageBox.warning(QApplication.activeWindow(), 'TreeLine',
                                      msg, QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.Yes)
            if ans == QMessageBox.Yes:
                self.pageLayout = tempPageLayout

    def paintData(self, printer):
        """Paint data to be printed to the printer.
        """
        pageNum = 1
        maxPageNum = self.outputGroup[-1].pageNum
        if self.printer.printRange() != QPrinter.AllPages:
            pageNum = self.printer.fromPage()
            maxPageNum = self.printer.toPage()
        painter = QPainter()
        if not painter.begin(self.printer):
            QMessageBox.warning(QApplication.activeWindow(),
                                'TreeLine', _('Error initializing printer'))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        while True:
            self.paintPage(pageNum, painter)
            if pageNum == maxPageNum:
                QApplication.restoreOverrideCursor()
                return
            pageNum += 1
            self.printer.newPage()

    def paintPage(self, pageNum, painter):
        """Paint data for the given page to the printer.

        Arguments:
            pageNum -- the page number to be printed
            painter -- the painter for this print job
        """
        totalNumPages = self.outputGroup[-1].pageNum
        headerDoc = self.headerFooterDoc(True, pageNum, totalNumPages)
        if headerDoc:
            layout = headerDoc.documentLayout()
            layout.setPaintDevice(self.printer)
            headerDoc.setTextWidth(self.pageLayout.paintRect().width() *
                                   self.printer.logicalDpiX())
            painter.save()
            topMargin = self.pageLayout.margins(QPageLayout.Inch).top()
            headerDelta = ((self.headerMargin - topMargin) *
                           self.printer.logicalDpiX())
            painter.translate(0, int(headerDelta))
            layout.draw(painter,
                        QAbstractTextDocumentLayout.PaintContext())
            painter.restore()
        painter.save()
        columnSpacing = int(self.columnSpacing * self.printer.logicalDpiX())
        columnDelta = ((self.pageLayout.paintRect().width() *
                        self.printer.logicalDpiX() -
                        columnSpacing * (self.numColumns - 1)) /
                       self.numColumns) + columnSpacing
        for columnNum in range(self.numColumns):
            if columnNum > 0:
                painter.translate(columnDelta, 0)
            self.paintColumn(pageNum, columnNum, painter)
        painter.restore()
        footerDoc = self.headerFooterDoc(False, pageNum, totalNumPages)
        if footerDoc:
            layout = footerDoc.documentLayout()
            layout.setPaintDevice(self.printer)
            footerDoc.setTextWidth(self.pageLayout.paintRect().width() *
                                   self.printer.logicalDpiX())
            painter.save()
            bottomMargin = self.pageLayout.margins(QPageLayout.Inch).bottom()
            footerDelta = ((bottomMargin - self.footerMargin) *
                           self.printer.logicalDpiX())
            painter.translate(0, self.pageLayout.paintRect().height() *
                              self.printer.logicalDpiX() +
                              int(footerDelta) - self.lineSpacing)
            layout.draw(painter,
                        QAbstractTextDocumentLayout.PaintContext())
            painter.restore()

    def paintColumn(self, pageNum, columnNum, painter):
        """Paint data for the given column to the printer.

        Arguments:
            pageNum -- the page number to be printed
            columnNum -- the column number to be printed
            painter -- the painter for this print job
        """
        columnItems = [item for item in self.outputGroup if
                       item.pageNum == pageNum and item.columnNum == columnNum]
        for item in columnItems:
            layout = item.doc.documentLayout()
            painter.save()
            painter.translate(item.level * self.indentSize, item.pagePos)
            layout.draw(painter,
                        QAbstractTextDocumentLayout.PaintContext())
            painter.restore()
        if self.drawLines:
            self.addPrintLines(pageNum, columnNum, columnItems, painter)

    def addPrintLines(self, pageNum, columnNum, columnItems, painter):
        """Paint lines between parent and child items on the page.

        Arguments:
            pageNum -- the page number to be printed
            columnNum -- the column number to be printed
            columnItems -- a list of items in this column
            painter -- the painter for this print job
        """
        parentsDrawn = set()
        horizOffset = self.indentSize // 2
        vertOffset = self.lineSpacing // 2
        heightAvail = (self.pageLayout.paintRect().height() *
                       self.printer.logicalDpiY())
        for item in columnItems:
            if item.level > 0:
                indent = item.level * self.indentSize
                vertPos = item.pagePos + vertOffset
                painter.drawLine(indent - horizOffset, vertPos,
                                 indent - self.lineSpacing // 4, vertPos)
                parent = item.parentItem
                while parent:
                    if parent in parentsDrawn:
                        break
                    lineStart = 0
                    lineEnd = heightAvail
                    if (parent.pageNum == pageNum and
                        parent.columnNum == columnNum):
                        lineStart = parent.pagePos + parent.height
                    if (parent.lastChildItem.pageNum == pageNum and
                        parent.lastChildItem.columnNum == columnNum):
                        lineEnd = parent.lastChildItem.pagePos + vertOffset
                    if (parent.lastChildItem.pageNum > pageNum or
                        (parent.lastChildItem.pageNum == pageNum and
                         parent.lastChildItem.columnNum >= columnNum)):
                        horizPos = ((parent.level + 1) * self.indentSize -
                                    horizOffset)
                        painter.drawLine(horizPos, lineStart,
                                         horizPos, lineEnd)
                    parentsDrawn.add(parent)
                    parent = parent.parentItem

    def formatHeaderFooter(self, header=True, pageNum=1, numPages=1):
        """Return an HTML table formatted header or footer.

        Return an empty string if no header/footer is defined.
        Arguments:
            header -- return header if True, footer if false
        """
        if header:
            textParts = printdialogs.splitHeaderFooter(self.headerText)
        else:
            textParts = printdialogs.splitHeaderFooter(self.footerText)
        if not textParts:
            return ''
        fileInfoFormat = self.localControl.structure.treeFormats.fileInfoFormat
        fileInfoNode = self.localControl.structure.fileInfoNode
        fileInfoFormat.updateFileInfo(self.localControl.filePathObj,
                                      fileInfoNode)
        fileInfoNode.data[fileInfoFormat.pageNumFieldName] = repr(pageNum)
        fileInfoNode.data[fileInfoFormat.numPagesFieldName] = repr(numPages)
        fileInfoFormat.changeOutputLines(textParts, keepBlanks=True)
        textParts = fileInfoFormat.formatOutput(fileInfoNode, keepBlanks=True)
        alignments = ('left', 'center', 'right')
        result = ['<table width="100%"><tr>']
        for text, align in zip(textParts, alignments):
            if text:
                result.append('<td align="{0}">{1}</td>'.format(align, text))
        if len(result) > 1:
            result.append('</tr></table>')
            return '\n'.join(result)
        return ''

    def headerFooterDoc(self, header=True, pageNum=1, numPages=1):
        """Return a text document for the header or footer.

        Return None if no header/footer is defined.
        Arguments:
            header -- return header if True, footer if false
        """
        text = self.formatHeaderFooter(header, pageNum, numPages)
        if text:
            doc = QTextDocument()
            doc.setHtml(text)
            doc.setDefaultFont(self.mainFont)
            frameFormat = doc.rootFrame().frameFormat()
            frameFormat.setBorder(0)
            frameFormat.setMargin(0)
            frameFormat.setPadding(0)
            doc.rootFrame().setFrameFormat(frameFormat)
            return doc
        return None

    def printSetup(self):
        """Show a dialog to set margins, page size and other printing options.
        """
        setupDialog = printdialogs.PrintSetupDialog(self, True, QApplication.
                                                    activeWindow())
        setupDialog.exec_()

    def printPreview(self):
        """Show a preview of printing results.
        """
        self.setupData()
        previewDialog = printdialogs.PrintPreviewDialog(self,QApplication.
                                                        activeWindow())
        previewDialog.previewWidget.paintRequested.connect(self.paintData)
        if globalref.genOptions['SaveWindowGeom']:
            previewDialog.restoreDialogGeom()
        previewDialog.exec_()

    def filePrint(self):
        """Show dialog and print tree output based on current options.
        """
        self.printer.setOutputFormat(QPrinter.NativeFormat)
        self.setupData()
        printDialog = QPrintDialog(self.printer, QApplication.activeWindow())
        if printDialog.exec_() == QDialog.Accepted:
            self.paintData(self.printer)

    def filePrintPdf(self):
        """Export to a PDF file with current options.
        """
        filters = ';;'.join((globalref.fileFilters['pdf'],
                             globalref.fileFilters['all']))
        defaultFilePath = str(globalref.mainControl.defaultPathObj())
        defaultFilePath = os.path.splitext(defaultFilePath)[0]
        if os.path.basename(defaultFilePath):
            defaultFilePath = '{0}.{1}'.format(defaultFilePath, 'pdf')
        filePath, selectFilter = QFileDialog.getSaveFileName(QApplication.
                                                    activeWindow(),
                                                    _('TreeLine - Export PDF'),
                                                    defaultFilePath, filters)
        if not filePath:
            return
        if not os.path.splitext(filePath)[1]:
            filePath = '{0}.{1}'.format(filePath, 'pdf')
        origFormat = self.printer.outputFormat()
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(filePath)
        self.adjustSpacing()
        self.setupData()
        self.paintData(self.printer)
        self.printer.setOutputFormat(origFormat)
        self.printer.setOutputFileName('')
        self.adjustSpacing()
