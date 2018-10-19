#******************************************************************************
# setup.py, provides a distutils script for use with cx_Freeze
#
# Creates a standalone windows executable
#
# Run the build process by running the command 'python setup.py build'
#
# If everything works well you should find a subdirectory in the build
# subdirectory that contains the files needed to run the application
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import sys
from cx_Freeze import setup, Executable
from treeline import __version__

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

extraFiles =  [('../doc', 'doc'), ('../icons', 'icons'),
               ('../samples', 'samples'), ('../source', 'source'),
               ('../templates', 'templates'),
               ('../translations', 'translations'), ('../win', '.')]

setup(name = 'treeline',
      version = __version__,
      description = 'TreeLine info storage program',
      options = {'build_exe': {'includes': ['atexit', 'PyQt5.sip'],
                               'include_files': extraFiles,
                               'excludes': ['*.pyc'],
                               'zip_include_packages': ['*'],
                               'zip_exclude_packages': [],
                               'include_msvcr': True,
                               'build_exe': '../../TreeLine-3.0'}},
      executables = [Executable('treeline.py', base=base,
                                icon='../win/treeline.ico')])
