#!/usr/bin/env python

#****************************************************************************
# httpload.py, provides a plugin to open TreeLine files from the web
#
# TreeLine, an information storage program
# Copyright (C) 2006, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#*****************************************************************************

"""httpLoad - opens TreeLine files from the web, v.0.2.0"""

import urllib2
import os
import locale
from PyQt4 import QtCore, QtGui


menuText = {'en': 'Open from &web...',
            'de': unicode('Aus dem &Internet \xc3\xb6ffnen', 'utf-8'),
            'es': 'Abrir desde la &web...',
            'fr': 'Ouvrir la page &web...',
            'pt': 'Abrir da &web...'}
dialogText = {'en': 'Enter web address',
              'de': 'Geben Sie die Internetadresse (URL) ein',
              'es': unicode('Introducir direcci\xc3\xb3n web', 'utf-8'),
              'fr': "Entrer l'adresse Internet",
              'pt': unicode('Informe o endere\xc3\xa7o web', 'utf-8')}
errorText = {'en': 'Could not open %s',
             'de': unicode('Konnte %s nicht \xc3\xb6ffnen', 'utf-8'),
             'es': 'No se ha podido abrir %s',
             'fr': "Impossible d'ouvrir %s",
             'pt': unicode('N\xc3\xa3o foi poss\xc3\xadvel abrir %s', 'utf-8')}


class HttpLoad:
    """Class for loading http files"""
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
        text = menuText.get(self.lang, menuText['en'])
        menu = self.interface.getPulldownMenu(0)
        actionBefore = menu.actions()[2]
        action = QtGui.QAction(text, self.interface.mainWin)
        action.connect(action, QtCore.SIGNAL('triggered(bool)'),
                       self.getAddress)
        menu.insertAction(actionBefore, action)

    def getAddress(self):
        """Prompt user for web address"""
        text = dialogText.get(self.lang, dialogText['en'])
        addr, ok = QtGui.QInputDialog.getText(self.interface.mainWin,
                                              'TreeLine', text)
        if ok:
            addr = unicode(addr)
            if ':' not in addr:
                addr = 'http://' + addr
            try:
                sock = urllib2.urlopen(addr)
                sock.name = addr.encode('utf-8')
                self.interface.openFile(sock, 1, 0)
            except IOError:
                text = errorText.get(self.lang, errorText['en'])
                QtGui.QMessageBox.warning(self.interface.mainWin, 'TreeLine',
                                          text % addr)

def main(interface):
    """Main connection"""
    return HttpLoad(interface)
