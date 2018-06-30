#!/usr/bin/env python3

#******************************************************************************
# httpload.py, provides a plugin to open TreeLine files from the web
#
# TreeLine, an information storage program
# Copyright (C) 2015, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

"""httpLoad - opens TreeLine files from the web, v.0.3.0
"""

import urllib.request
from PyQt4 import QtCore, QtGui


menuText = {'en': 'Open from &Web...',
            'de': 'Aus dem &Internet \xc3\xb6ffnen',
            'es': 'Abrir desde la &web...',
            'fr': 'Ouvrir la page &web...',
            'pt': 'Abrir da &web...'}
dialogText = {'en': 'Enter web address',
              'de': 'Geben Sie die Internetadresse (URL) ein',
              'es': 'Introducir direcci\xc3\xb3n web',
              'fr': "Entrer l'adresse Internet",
              'pt': 'Informe o endere\xc3\xa7o web'}
errorText = {'en': 'Could not open {0}',
             'de': 'Konnte {0} nicht \xc3\xb6ffnen',
             'es': 'No se ha podido abrir {0}',
             'fr': "Impossible d'ouvrir {0}",
             'pt': 'N\xc3\xa3o foi poss\xc3\xadvel abrir {0}'}


class HttpLoad:
    """Class for loading http files.
    """
    def __init__(self, interface):
        """Initialize the plugin and its menu.

        Arguments:
            interface -- the treeline plugin interface
        """
        self.interface = interface
        self.interface.setNewWindowCallback(self.addMenu)
        self.lang = interface.getLanguage()
        if not self.lang:
            self.lang = 'en'
        self.lang = self.lang[:2]
        text = menuText.get(self.lang, menuText['en'])
        self.action = QtGui.QAction(text, self.interface.mainControl())
        self.action.triggered.connect(self.getAddress)
        self.addMenu()

    def addMenu(self):
        """Add the open from web menu item.
        """
        menu = self.interface.getPulldownMenu(0)
        actionBefore = menu.actions()[2]
        menu.insertAction(actionBefore, self.action)

    def getAddress(self):
        """Prompt user for web address and open it.
        """
        text = dialogText.get(self.lang, dialogText['en'])
        addr, ok = QtGui.QInputDialog.getText(self.interface.getActiveWindow(),
                                              'TreeLine', text)
        if ok:
            if ':' not in addr:
                addr = 'http://' + addr
            try:
                sock = urllib.request.urlopen(addr)
                sock.name = addr
                self.interface.openFile(sock)
            except IOError:
                text = errorText.get(self.lang, errorText['en'])
                QtGui.QMessageBox.warning(self.interface.getActiveWindow(),
                                          'TreeLine', text.format(addr))

def main(interface):
    """Main interface connection.
    """
    return HttpLoad(interface)
