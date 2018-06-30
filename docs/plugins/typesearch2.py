""" Find By Item Type - highlights all items of a given data type

    Version 1.0.1a -- ported to Qt4 by hg

    TODO: retrieve the Tools menu by something other than index
    TODO: localize
    TODO: optimize: replace openParents() to speed up tree configuration
    TODO: optimize: use a prepared node list during highlighting

    Copyright (C) 2007 Jan Hustak, http://www.journey.sk/
    The use of this software is governed by the same license terms
    as the TreeLine application (see http://www.bellz.org/treeline/) """

import os
import locale
from PyQt4 import QtCore, QtGui

menuText = {'en': 'Find items by type',
            'de': unicode('Elemente eines Typs &finden', 'utf-8')
            }
resetText = {'en': 'Reset search by type',
            'de': unicode('Suche nach Typ &zur\xc3\xbccksetzen', 'utf-8')
            }

def main(interface):
  return SearchByItemTypePlugin(interface)

class SearchByItemTypePlugin:
  def __init__(self, interface):
    self.interface = interface
    self.lang = os.environ.get('LANG', '')
    if not self.lang:
      try:
        self.lang = locale.getdefaultlocale()[0]
      except ValueError:
        pass
    if not self.lang:
      self.lang = 'en'
    self.lang = self.lang[:2]
    typemenutext = menuText.get(self.lang, menuText['en'])
    resetactiontext = resetText.get(self.lang, resetText['en'])
    self.parentMenu = self.interface.getPulldownMenu(4) # should be the Tools menu
    self.parentMenu.addSeparator()
    self.typeMenu = self.parentMenu.addMenu(SearchByItemTypePlugin.resultIcon,
                                            typemenutext)
    self.resetaction = QtGui.QAction(resetactiontext, self.interface.mainWin)
    self.parentMenu.addAction(self.resetaction)
    self.parentMenu.connect(self.resetaction,
                            QtCore.SIGNAL('triggered(bool)'), self.doReset)
    self.interface.setFileOpenCallback(self.updateTypeMenu)

  def updateTypeMenu(self):
    self.typeMenu.clear()
    self.typeactions = {}
    typeNames = self.interface.getNodeFormatNames()
    for name in typeNames:
      self.typeactions[name] = QtGui.QAction(name, self.interface.mainWin)
      self.typeactions[name].setIcon(SearchByItemTypePlugin.resultIcon)
      self.typeMenu.addAction(self.typeactions[name])
      self.typeMenu.connect(self.typeactions[name],
                            QtCore.SIGNAL('activated(int)'), self.doSearch)

  def doReset(self):
    self.interface.updateViews()
    
  def doSearch(self, typeIndex):
    sender = self.interface.mainWin.sender()
    typeName = sender.text()
    self.interface.mainWin.statusBar().showMessage(sender.text() +
                                                   ' was searched')
    rootNode = self.interface.getRootNode()
    self.interface.changeSelection([rootNode])  # move selection out of the way
    rootNode.openBranch(False)                  # reset tree structure
    self.searchSubtree(rootNode, typeName)      # reconfigure tree structure
    self.interface.updateViews()                # initialize widgets
    self.highlightSubtree(rootNode, typeName)   # apply highlights

  def searchSubtree(self, node, typeName):
    if node.formatName == typeName:
      node.openParents(False)
    for child in node.childList:
      self.searchSubtree(child, typeName)

  def highlightSubtree(self, node, typeName):
    if node.formatName == typeName:
      node.viewData.setIcon(0, SearchByItemTypePlugin.resultIcon)
    for child in node.childList:
      self.highlightSubtree(child, typeName)

  resultIcon = QtGui.QIcon(QtGui.QPixmap(["16 16 22 1", ". c none",
  "a c #000000", "i c #202000", "t c #454500", "c c #505030", "y c #777777",
  "x c #7e7e88", "p c #808000", "j c #828200", "r c #858500", "n c #888800",
  "v c #8c8c00", "b c #9090a0", "u c #969600", "q c #a4a428", "m c #abab6f",
  "o c #acac20", "w c #b4b428", "k c #b7978f", "h c #caca18", "# c #d7a700",
  "d c #ffc0a0",
  "................", "................", "................",
  "................", "................", "................",
  "................", "...###########..", "abcdddddddddddh.",
  "aidddddddjkkkm..", "andddddddo......", "apddddddq.......",
  "arddddd#........", "atuvvnw.........", "ax..............",
  "yy.............."]))
