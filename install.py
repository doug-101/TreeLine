#!/usr/bin/env python3

"""
****************************************************************************
 install.py, Linux install script for TreeLine

 Copyright (C) 2018, Douglas W. Bell

 This is free software; you can redistribute it and/or modify it under the
 terms of the GNU General Public License, either Version 2 or any later
 version.  This program is distributed in the hope that it will be useful,
 but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
*****************************************************************************
"""

import sys
import os.path
import getopt
import shutil
import compileall
import py_compile
import glob
import re
import subprocess

prefixDir = '/usr/local'
buildRoot = '/'
progName = 'treeline'
docDir = 'share/doc/{0}'.format(progName)
templateDir = 'share/{0}/templates'.format(progName)
iconToolDir = 'share/icons/{0}'.format(progName)
testSpell = True

def usage(exitCode=2):
    """Display usage info and exit.

    Arguments:
        exitCode -- the code to retuen when exiting.
    """
    global prefixDir
    global buildRoot
    print('Usage:')
    print('    python install.py [-h] [-p dir] [-d dir] [-t dir] [-i dir] '
          '[-b dir] [-s] [-x]')
    print('where:')
    print('    -h         display this help message')
    print('    -p dir     install prefix [default: {0}]'.format(prefixDir))
    print('    -d dir     documentaion dir [default: <prefix>/{0}]'
          .format(docDir))
    print('    -t dir     template dir [default: <prefix>/{0}]'
          .format(templateDir))
    print('    -i dir     tool icon dir [default: <prefix>/{0}]'
          .format(iconToolDir))
    print('    -b dir     temporary build root for packagers [default: {0}]'
          .format(buildRoot))
    print('    -s         skip language translation files')
    print('    -x         skip all dependency checks (risky)')
    sys.exit(exitCode)


def cmpVersions(versionStr, reqdTuple):
    """Return True if point-sep values in versionStr are >= reqdTuple.

    Arguments:
        versionStr -- a string with point-separated version numbers
        reqdTuple -- a tuple of version integers for the minimum acceptable
    """
    match = re.search(r'[0-9\.]+', versionStr)
    if not match:
        return False
    versionStr = match.group()
    versionList = [int(val) for val in versionStr.split('.') if val]
    reqdList = list(reqdTuple)
    while len(versionList) < len(reqdList):
        versionList.append(0)
    while len(reqdList) < len(versionList):
        reqdList.append(0)
    if versionList >= reqdList:
        return True
    return False

def copyDir(srcDir, dstDir):
    """Copy all regular files from srcDir to dstDir.

    dstDir is created if necessary.
    Arguments:
        srcDir -- the source dir path
        dstDir -- the destination dir path
    """
    try:
        if not os.path.isdir(dstDir):
            os.makedirs(dstDir)
        names = os.listdir(srcDir)
        for name in names:
            srcPath = os.path.join(srcDir, name)
            if os.path.isfile(srcPath):
                shutil.copy2(srcPath, os.path.join(dstDir, name))
    except (IOError, OSError) as e:
        if str(e).find('Permission denied') >= 0:
            print('Error - must be root to install files')
            cleanSource()
            sys.exit(4)
        raise

def createWrapper(execDir, execName):
    """Create a wrapper executable file for a python script in execDir.

    Arguments:
        execDir -- the path where the executable is placed
        execName -- the name for the executable file
    """
    text = '#!/bin/sh\n\nexec {0} {1}/{2}.py "$@"'.format(sys.executable,
                                                          execDir,
                                                          execName)
    with open(execName, 'w') as f:
        f.write(text)
    os.chmod(execName, 0o755)

def replaceLine(path, origLineStart, newLine):
    """Replaces lines with origLineStart with newLine and rewrites the file.

    Arguments:
        path -- the file to modify
        origLineStart -- the beginning of the line to be replaced
        newLine -- the replacement line
    """
    with open(path, 'r') as f:
        lines = f.readlines()
    with open(path, 'w') as f:
        for line in lines:
            if line.startswith(origLineStart):
                f.write(newLine)
            else:
                f.write(line)

def spellCheck(cmdList):
    """Try spell checkers from list, print result.

    Arguments:
        cmdList -- a list of spell checkers to check
    """
    for cmd in cmdList:
        try:
            p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            p.stdout.readline()
            p.stdin.write(b'!\n')
            p.stdin.flush()
            p.stdin.close()
            p.stdout.close()
            print('  Spell Checker {0} -> OK'.format(cmd.split()[0]))
            return
        except:
            pass
    print('  Spell Checker not found -> install aspell, ispell or hunspell')
    print('                             if spell checking is desired')

def cleanSource():
    """Remove any temporary files added to untarred dirs.
    """
    for name in glob.glob(os.path.join('source', '*.py[co]')):
        os.remove(name)
    removeDir(os.path.join('source', '__pycache__'))
    global progName
    if os.path.isfile(progName):
        os.remove(progName)

def removeDir(dir):
    """Remove dir and all files under it, ignore errors.

    Arguments:
        dir -- the directory to remove
    """
    try:
        shutil.rmtree(dir, 1)
    except:    # shouldn't be needed with ignore error param, but
        pass   # some python versions have a bug

def main():
    """Main installer function.
    """
    optLetters = 'hp:d:t:i:b:sx'
    try:
        opts, args = getopt.getopt(sys.argv[1:], optLetters)
    except getopt.GetoptError:
        usage(2)
    global prefixDir
    global docDir
    global templateDir
    global iconToolDir
    global buildRoot
    global progName
    depCheck = True
    translated = True
    for opt, val in opts:
        if opt == '-h':
            usage(0)
        elif opt == '-p':
            prefixDir = os.path.abspath(val)
        elif opt == '-d':
            docDir = val
        elif opt == '-t':
            templateDir = val
        elif opt == '-i':
            iconToolDir = val
        elif opt == '-b':
            buildRoot = val
        elif opt == '-s':
            translated = False
        elif opt == '-x':
            depCheck = False
    if not os.path.isfile('install.py'):
        print('Error - {0} files not found'.format(progName))
        print('The directory containing "install.py" must be current')
        sys.exit(4)
    if (os.path.isdir('source') and
        not os.path.isfile('source/{0}.py'.format(progName))):
        print('Error - source files not found')
        print('Retry the extraction from the tar archive')
        sys.exit(4)
    if depCheck:
        print('Checking dependencies...')
        pyVersion = sys.version_info[:3]
        pyVersion = '.'.join([str(num) for num in pyVersion])
        if cmpVersions(pyVersion, (3, 5)):
            print('  Python Version {0} -> OK'.format(pyVersion))
        else:
            print('  Python Version {0} -> Sorry, 3.5 or higher is required'
                  .format(pyVersion))
            sys.exit(3)
        try:
            from PyQt5 import QtCore, QtWidgets
        except:
            print('  PyQt not found -> Sorry, PyQt 5.8 or higher is required'
                  ' and must be built for Python 3')
            sys.exit(3)
        qtVersion = QtCore.qVersion()
        if cmpVersions(qtVersion, (5, 8)):
            print('  Qt Version {0} -> OK'.format(qtVersion))
        else:
            print('  Qt Version {0} -> Sorry, 5.8 or higher is required'
                  .format(qtVersion))
            sys.exit(3)
        pyqtVersion = QtCore.PYQT_VERSION_STR
        if cmpVersions(pyqtVersion, (5, 8)):
            print('  PyQt Version {0} -> OK'.format(pyqtVersion))
        else:
            print('  PyQt Version {0} -> Sorry, 5.8 or higher is required'
                  .format(pyqtVersion))
            sys.exit(3)
        global testSpell
        if testSpell:
            spellCheck(['aspell -a', 'ispell -a', 'hunspell -a'])

    pythonPrefixDir = os.path.join(prefixDir, 'share', progName)
    pythonBuildDir = os.path.join(buildRoot, pythonPrefixDir[1:])

    if os.path.isdir('source'):
        print('Installing files...')
        print('  Copying python files to {0}'.format(pythonBuildDir))
        removeDir(pythonBuildDir)         # remove old?
        copyDir('source', pythonBuildDir)
    if os.path.isfile('source/plugininterface.py'):
        pluginBuildDir = os.path.join(pythonBuildDir, 'plugins')
        print('  Creating plugins directory if necessary')
        if not os.path.isdir(pluginBuildDir):
            os.makedirs(pluginBuildDir)
    if os.path.isdir('translations') and translated:
        translationDir = os.path.join(pythonBuildDir, 'translations')
        print('  Copying translation files to {0}'.format(translationDir))
        copyDir('translations', translationDir)
    if os.path.isdir('doc'):
        docPrefixDir = docDir.replace('<prefix>/', '')
        if not os.path.isabs(docPrefixDir):
            docPrefixDir = os.path.join(prefixDir, docPrefixDir)
        docBuildDir = os.path.join(buildRoot, docPrefixDir[1:])
        print('  Copying documentation files to {0}'.format(docBuildDir))
        copyDir('doc', docBuildDir)
        if not translated:
            for name in glob.glob(os.path.join(docBuildDir,
                                               '*_[a-z][a-z].')):
                os.remove(name)
        # update help file location in main python script
        replaceLine(os.path.join(pythonBuildDir, '{0}.py'.format(progName)),
                    'docPath = None',
                    'docPath = \'{0}\'   # modified by install script\n'
                    .format(docPrefixDir))
        if os.path.isdir('samples'):
            sampleBuildDir = os.path.join(docBuildDir, 'samples')
            print('  Copying sample files to {0}'.format(sampleBuildDir))
            copyDir('samples', sampleBuildDir)
            # update sample file location in main python script
            replaceLine(os.path.join(pythonBuildDir,
                                     '{0}.py'.format(progName)),
                        'samplePath = None',
                        'samplePath = \'{0}\'   # modified by install script\n'
                        .format(os.path.join(docPrefixDir, 'samples')))
    if os.path.isdir('templates'):
        templatePrefixDir = templateDir.replace('<prefix>/', '')
        if not os.path.isabs(templatePrefixDir):
            templatePrefixDir = os.path.join(prefixDir, templatePrefixDir)
        templateBuildDir = os.path.join(buildRoot, templatePrefixDir[1:])
        print('  Copying template files to {0}'.format(templateBuildDir))
        copyDir('templates', templateBuildDir)
        if not translated:
            for name in glob.glob(os.path.join(templateBuildDir, '*.trl')):
                if 'en_' not in os.path.basename(name):
                    os.remove(name)
        # update template file location in main python script
        replaceLine(os.path.join(pythonBuildDir, '{0}.py'.format(progName)),
                    'templatePath = None',
                    'templatePath = \'{0}\'   # modified by install script\n'
                    .format(templatePrefixDir))
    if os.path.isdir('data'):
        dataPrefixDir = os.path.join(prefixDir, 'share', progName, 'data')
        dataBuildDir = os.path.join(buildRoot, dataPrefixDir[1:])
        print('  Copying data files to {0}'.format(dataBuildDir))
        removeDir(dataBuildDir)   # remove old?
        copyDir('data', dataBuildDir)
        if not translated:
            for name in glob.glob(os.path.join(dataBuildDir,
                                               '*_[a-z][a-z].dat')):
                os.remove(name)
        # update data file location in main python script
        replaceLine(os.path.join(pythonBuildDir, '{0}.py'.format(progName)),
                    'dataFilePath = None',
                    'dataFilePath =  \'{0}\'   # modified by install script\n'
                    .format(dataPrefixDir))
    if os.path.isdir('icons'):
        iconPrefixDir = iconToolDir.replace('<prefix>/', '')
        if not os.path.isabs(iconPrefixDir):
            iconPrefixDir = os.path.join(prefixDir, iconPrefixDir)
        iconBuildDir = os.path.join(buildRoot, iconPrefixDir[1:])
        print('  Copying tool icon files to {0}'.format(iconBuildDir))
        copyDir('icons', iconBuildDir)
        # update icon location in main python script
        replaceLine(os.path.join(pythonBuildDir, '{0}.py'.format(progName)),
                    'iconPath = None',
                    'iconPath =  \'{0}\'   # modified by install script\n'
                    .format(iconPrefixDir))
        if os.path.isdir('icons/toolbar'):
            iconToolBuildDir = os.path.join(iconBuildDir, 'toolbar')
            copyDir('icons/toolbar', iconToolBuildDir)
            if os.path.isdir('icons/toolbar/16x16'):
                copyDir('icons/toolbar/16x16',
                        os.path.join(iconToolBuildDir, '16x16'))
            if os.path.isdir('icons/toolbar/32x32'):
                copyDir('icons/toolbar/32x32', 
                        os.path.join(iconToolBuildDir, '32x32'))
        if os.path.isdir('icons/tree'):
            copyDir('icons/tree', os.path.join(iconBuildDir, 'tree'))
        if os.path.isfile(os.path.join('icons', progName + '-icon.png')):
            pngIconPrefixDir = os.path.join(prefixDir, 'share', 'icons',
                                            'hicolor', '48x48', 'apps')
            pngIconBuildDir = os.path.join(buildRoot, pngIconPrefixDir[1:])
            print('  Copying app icon files to {0}'.format(pngIconBuildDir))
            if not os.path.isdir(pngIconBuildDir):
                os.makedirs(pngIconBuildDir)
            shutil.copy2(os.path.join('icons', progName + '-icon.png'),
                         pngIconBuildDir)
        if os.path.isfile(os.path.join('icons', progName + '-icon.svg')):
            svgIconPrefixDir = os.path.join(prefixDir, 'share', 'icons',
                                            'hicolor', 'scalable', 'apps')
            svgIconBuildDir = os.path.join(buildRoot, svgIconPrefixDir[1:])
            print('  Copying app icon files to {0}'.format(svgIconBuildDir))
            if not os.path.isdir(svgIconBuildDir):
                os.makedirs(svgIconBuildDir)
            shutil.copy2(os.path.join('icons', progName + '-icon.svg'),
                         svgIconBuildDir)
    if os.path.isfile(progName + '.desktop'):
        desktopPrefixDir = os.path.join(prefixDir, 'share', 'applications')
        desktopBuildDir = os.path.join(buildRoot, desktopPrefixDir[1:])
        print('  Copying desktop file to {0}'.format(desktopBuildDir))
        if not os.path.isdir(desktopBuildDir):
            os.makedirs(desktopBuildDir)
        shutil.copy2(progName + '.desktop', desktopBuildDir)

    if os.path.isdir('source'):
        createWrapper(pythonPrefixDir, progName)
        binBuildDir = os.path.join(buildRoot, prefixDir[1:], 'bin')
        print('  Copying executable file "{0}" to {1}'
              .format(progName, binBuildDir))
        if not os.path.isdir(binBuildDir):
            os.makedirs(binBuildDir)
        shutil.copy2(progName, binBuildDir)
        compileall.compile_dir(pythonBuildDir, ddir=prefixDir)
        cleanSource()
        print('Install complete.')


if __name__ == '__main__':
    main()
