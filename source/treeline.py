#!/usr/bin/env python3

#******************************************************************************
# treeline.py, the main program file
#
# TreeLine, an information storage program
# Copyright (C) 2019, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

__progname__ = 'TreeLine'
__version__ = '3.1.3+'
__author__ = 'Doug Bell'

docPath = None         # modified by install script if required
iconPath = None        # modified by install script if required
templatePath = None    # modified by install script if required
samplePath = None      # modified by install script if required
translationPath = 'translations'


import sys
import pathlib
import os.path
import argparse
import locale
import builtins
from PyQt5.QtCore import QCoreApplication, QTranslator
from PyQt5.QtWidgets import QApplication, qApp


def loadTranslator(fileName, app):
    """Load and install qt translator, return True if sucessful.

    Arguments:
        fileName -- the translator file to load
        app -- the main QApplication
    """
    translator = QTranslator(app)
    # use abspath() - pathlib's resolve() can be buggy with network drives
    modPath = pathlib.Path(os.path.abspath(sys.path[0]))
    if modPath.is_file():
        modPath = modPath.parent  # for frozen binary
    path = modPath / translationPath
    result = translator.load(fileName, str(path))
    if not result:
        path = modPath.parent / translationPath
        result = translator.load(fileName, str(path))
    if not result:
        path = modPath.parent / 'i18n' / translationPath
        result = translator.load(fileName, str(path))
    if result:
        QCoreApplication.installTranslator(translator)
        return True
    else:
        print('Warning: translation file "{0}" could not be loaded'.
              format(fileName))
        return False

def setupTranslator(app, lang=''):
    """Set language, load translators and setup translator functions.

    Return the language setting
    Arguments:
        app -- the main QApplication
        lang -- language setting from the command line
    """
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass
    if not lang:
        lang = os.environ.get('LC_MESSAGES', '')
        if not lang:
            lang = os.environ.get('LANG', '')
            if not lang:
                try:
                    lang = locale.getdefaultlocale()[0]
                except ValueError:
                    pass
                if not lang:
                    lang = ''
    numTranslators = 0
    if lang and lang[:2] not in ['C', 'en']:
        numTranslators += loadTranslator('qt_{0}'.format(lang), app)
        numTranslators += loadTranslator('treeline_{0}'.format(lang),
                                         app)

    def translate(text, comment=''):
        """Translation function, sets context to calling module's filename.

        Arguments:
            text -- the text to be translated
            comment -- a comment used only as a guide for translators
        """
        try:
            frame = sys._getframe(1)
            fileName = frame.f_code.co_filename
        finally:
            del frame
        context = pathlib.Path(fileName).stem
        return QCoreApplication.translate(context, text, comment)

    def markNoTranslate(text, comment=''):
        """Dummy translation function, only used to mark text.

        Arguments:
            text -- the text to be translated
            comment -- a comment used only as a guide for translators
        """
        return text

    if numTranslators:
        builtins._ = translate
    else:
        builtins._ = markNoTranslate
    builtins.N_ = markNoTranslate
    return lang


exceptDialog = None

def handleException(excType, value, tb):
    """Handle uncaught exceptions, show debug info to the user.

    Called from sys.excepthook.
    Arguments:
        excType -- execption class
        value -- execption error text
        tb -- the traceback object
    """
    import miscdialogs
    global exceptDialog
    exceptDialog = miscdialogs.ExceptionDialog(excType, value, tb)
    exceptDialog.show()
    if not QApplication.activeWindow():
        qApp.exec_()  # start event loop in case it's not running yet


if __name__ == '__main__':
    """Main event loop for TreeLine
    """
    app = QApplication(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang', help='language code for GUI translation')
    parser.add_argument('fileList', nargs='*', metavar='filename',
                        help='input filename(s) to load')
    args = parser.parse_args()
    # use abspath() - pathlib's resolve() can be buggy with network drives
    pathObjects = [pathlib.Path(os.path.abspath(path)) for path in
                   args.fileList]

    # must setup translator before any treeline module imports
    lang = setupTranslator(app, args.lang)

    import globalref
    globalref.localTextEncoding = locale.getpreferredencoding()

    sys.excepthook = handleException

    import treemaincontrol
    treeMainControl = treemaincontrol.TreeMainControl(pathObjects)
    app.exec_()
