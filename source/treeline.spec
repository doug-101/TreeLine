# -*- mode: python -*-

#******************************************************************************
# treeline.spec, provides settings for use with PyInstaller
#
# Creates a standalone windows executable
#
# Run the build process by running the command 'pyinstaller treeline.spec'
#
# If everything works well you should find a 'dist/treeline' subdirectory
# that contains the files needed to run the application
#
# TreeLine, an information storage program
# Copyright (C) 2020, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

block_cipher = None

extraFiles = [('../doc', 'doc'),
              ('../icons', 'icons'),
              ('../samples', 'samples'),
              ('../source/*.py', 'source'),
              ('../source/*.pro', 'source'),
              ('../source/*.spec', 'source'),
              ('../templates', 'templates'),
              ('../translations', 'translations'),
              ('../win/*.*', '.')]

a = Analysis(['treeline.py'],
             pathex=['C:\\git\\treeline\\devel\\source'],
             binaries=[],
             datas=extraFiles,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='treeline',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='..\\win\\treeline.ico')
a.binaries = a.binaries - TOC([('d3dcompiler_47.dll', None, None),
                               ('libcrypto-1_1.dll', None, None),
                               ('libeay32.dll', None, None),
                               ('libglesv2.dll', None, None),
                               ('libssl-1_1.dll', None, None),
                               ('opengl32sw.dll', None, None),
                               ('qt5dbus.dll', None, None),
                               ('qt5qml.dll', None, None),
                               ('qt5qmlmodels.dll', None, None),
                               ('qt5quick.dll', None, None),
                               ('qt5websockets.dll', None, None)])
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='treeline')
