#!/usr/bin/env python3

#******************************************************************************
# treeline.py, the main program file
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

__progname__ = 'TreeLine'
__version__ = '2.9.0'
__author__ = 'Doug Bell'

docPath = None         # modified by install script if required
iconPath = None        # modified by install script if required
templatePath = None    # modified by install script if required
samplePath = None      # modified by install script if required
translationPath = 'translations'


import sys
import os.path
import argparse
import locale
import builtins
from PyQt5.QtWidgets import QApplication


def markNoTranslate(text, comment=''):
    """Dummy translation function, only used to mark text.

    Arguments:
        text -- the text to be translated
        comment -- a comment used only as a guide for translators
    """
    return text

builtins._ = markNoTranslate
builtins.N_ = markNoTranslate


if __name__ == '__main__':
    """Main event loop for TreeLine
    """
    app = QApplication(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument('fileList', nargs='*', metavar='filename',
                        help='input filename(s) to load')
    args = parser.parse_args()

    import treemaincontrol
    treeMainControl = treemaincontrol.TreeMainControl(args.fileList)
    app.exec_()
