""" Find By Item Type - highlights all items of a given data type

    Version 1.0.1

    TODO: retrieve the Tools menu by something other than index
    TODO: localize
    TODO: optimize: replace openParents() to speed up tree configuration
    TODO: optimize: use a prepared node list during highlighting

    Copyright (C) 2007 Jan Hustak, http://www.journey.sk/
    The use of this software is governed by the same license terms
    as the TreeLine application (see http://www.bellz.org/treeline/) """

from qt import QIconSet, QPixmap, QPopupMenu, SIGNAL

def main(pluginContext):
  return SearchByItemTypePlugin(pluginContext)

class SearchByItemTypePlugin:

  def __init__(self, pluginContext):
    parentMenu = pluginContext.getPulldownMenu(4) # should be the Tools menu
    self.typeMenu = QPopupMenu(parentMenu)
    iconWrapper = QIconSet(SearchByItemTypePlugin.resultIcon)
    parentMenu.insertItem(iconWrapper, _('Find Items By Type'), self.typeMenu)
    parentMenu.connect(self.typeMenu, SIGNAL('activated(int)'), self.doSearch)
    self.context = pluginContext
    self.context.setFileOpenCallback(self.updateTypeMenu)

  def updateTypeMenu(self):
    typeNames = self.context.getNodeFormatNames()
    self.typeMenu.clear()
    index = 0
    for name in typeNames:
      self.typeMenu.insertItem(name, index)
      index += 1

  def doSearch(self, typeIndex):
    typeName = self.context.getNodeFormatNames()[typeIndex]
    rootNode = self.context.getRootNode()
    self.context.changeSelection([rootNode])  # move selection out of the way
    rootNode.openBranch(False)                # reset tree structure
    self.searchSubtree(rootNode, typeName)    # reconfigure tree structure
    self.context.updateViews()                # initialize widgets
    self.highlightSubtree(rootNode, typeName) # apply highlights

  def searchSubtree(self, node, typeName):
    if node.nodeFormat.name == typeName:
      node.openParents(False)
    for child in node.childList:
      self.searchSubtree(child, typeName)

  def highlightSubtree(self, node, typeName):
    if node.nodeFormat.name == typeName:
      node.viewData.setPixmap(0, SearchByItemTypePlugin.resultIcon)
    for child in node.childList:
      self.highlightSubtree(child, typeName)

  resultIcon = QPixmap(["16 16 22 1", ". c none",
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
  "yy.............."])