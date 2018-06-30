#!/usr/bin/env python

#****************************************************************************
# httpload.py, provides a plugin to open TreeLine files from the web
#
# TreeLine, an information storage program
# Copyright (C) 2004, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, Version 2.  This program is
# distributed in the hope that it will be useful, but WITTHOUT ANY WARRANTY.
#*****************************************************************************

"""httpLoad - opens TreeLine files from the web, v.0.1.4"""

import urllib2
import os
import locale
from qt import *


menuText = {'en': 'Open from &web...',
            'de': unicode('Aus dem &Internet \xc3\xb6ffnen', 'utf-8'),
            'es': 'Abrir desde la &web...',
            'fr': 'Ouvrir la page &web...',
            'pt': 'Abrir da &web...',
            'ru': unicode('\xd0\x9e\xd1\x82\xd0\xba\xd1\x80\xd1\x8b\xd1\x82'\
                          '\xd1\x8c \xd0\xb8\xd0\xb7 &\xd1\x81\xd0\xb5\xd1'\
                          '\x82\xd0\xb8...')}
dialogText = {'en': 'Enter web address',
              'de': 'Geben Sie die Internetadresse (URL) ein',
              'es': unicode('Introducir direcci\xc3\xb3n web', 'utf-8'),
              'fr': "Entrer l'adresse Internet",
              'pt': unicode('Informe o endere\xc3\xa7o web', 'utf-8'),
              'ru': unicode('\xd0\x92\xd0\xb2\xd0\xb5\xd1\x81\xd1\x82\xd0\xb8'\
                            ' \xd1\x81\xd0\xb5\xd1\x82\xd0\xb5\xd0\xb2\xd0'\
                            '\xbe\xd0\xb9 \xd0\xb0\xd0\xb4\xd1\x80\xd0\xb5'\
                            '\xd1\x81')}
errorText = {'en': 'Could not open %s',
             'de': unicode('Konnte %s nicht \xc3\xb6ffnen', 'utf-8'),
             'es': 'No se ha podido abrir %s',
             'fr': "Impossible d'ouvrir %s",
             'pt': unicode('N\xc3\xa3o foi poss\xc3\xadvel abrir %s', 'utf-8'),
             'ru': unicode('\xd0\x9d\xd0\xb5\xd0\xb2\xd0\xbe\xd0\xb7\xd0\xbc'\
                           '\xd0\xbe\xd0\xb6\xd0\xbd\xd0\xbe \xd0\xbe\xd1\x82'\
                           '\xd0\xba\xd1\x80\xd1\x8b\xd1\x82\xd1\x8c %s')}


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
        self.interface.getPulldownMenu(0).insertItem(text, self.getAddress,
                                                     0, -1, 2)

    def getAddress(self):
        """Prompt user for web address"""
        text = dialogText.get(self.lang, dialogText['en'])
        addr, ok = QInputDialog.getText('TreeLine', text,
                                        QLineEdit.Normal, '',
                                        self.interface.mainWin)
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
                QMessageBox.warning(self.interface.mainWin, 'TreeLine',
                                    text % addr)

def main(interface):
    """Main connection"""
    return HttpLoad(interface)
