#!/usr/bin/env python3

#******************************************************************************
# globalref.py, provides a module for access to a few global variables
#
# TreeLine, an information storage program
# Copyright (C) 2017, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

mainControl = None

genOptions = None
miscOptions = None
histOptions = None
toolbarOptions = None
keyboardOptions = None

toolIcons = None
treeIcons = None

localTextEncoding = ''
lang = ''

fileFilters = {'trlnopen': '{} (*.trln *.trln.gz *.trl)'.
                           format(_('All TreeLine Files')),
               'trlnv3': '{} (*.trln *.trln.gz)'.format(_('TreeLine Files')),
               'trlnsave': '{} (*.trln)'.format(_('TreeLine Files')),
               'trlngz': '{} (*.trln *.trln.gz)'.
                         format(_('TreeLine Files - Compressed')),
               'trlnenc': '{} (*.trln)'.
                          format(_('TreeLine Files - Encrypted')),
               'trl': '{} (*.trl *.xml)'.format(_('Old TreeLine Files')),
               'all': '{} (*)'.format(_('All Files')),
               'html': '{} (*.html *.htm)'.format(_('HTML Files')),
               'txt': '{} (*.txt)'.format(_('Text Files')),
               'xml': '{} (*.xml)'.format(_('XML Files')),
               'csv': '{} (*.csv)'.format(_('CSV (Comma Delimited) Files')),
               'odt': '{} (*.odt)'.format(_('ODF Text Files')),
               'hjt': '{} (*.hjt)'.format(_('Treepad Files')),
               'pdf': '{} (*.pdf)'.format(_('PDF Files'))}
