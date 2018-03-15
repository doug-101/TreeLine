#!/usr/bin/env python3

#******************************************************************************
# urltools.py, provides functions for parsing and modifying URLs.
#
# TreeLine, an information storage program
# Copyright (C) 2018, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************


import re
import sys
import os.path

_urlRegExp = re.compile(r'([a-z]{2,}://)?(?:/?([a-z]:))?(.*)', re.IGNORECASE)


def splitUrl(url):
    """Return a tuple of scheme, drive letter and address.

    If any are not present, return empty strings.
    Arguments:
        url -- a string with the original URL
    """
    if os.sep == '\\':
        url = url.replace('\\', '/')
    scheme, drive, address = _urlRegExp.match(url).groups('')
    scheme = scheme[:-3]
    if not scheme and url.startswith('mailto:'):
        scheme = 'mailto'
        drive = ''
        address = url[7:]
    return (scheme, drive, address)

def extractScheme(url):
    """Return the scheme from this URL, or an empty string if none is given.

    Arguments:
        url -- a string with the original URL
    """
    scheme, drive, address = splitUrl(url)
    return scheme

def extractAddress(url):
    """Remove the scheme from this URL and return the address.

    Includes the drive letter if present.

    Arguments:
        url -- a string with the original URL
    """
    scheme, drive, address = splitUrl(url)
    return drive + address

def replaceScheme(scheme, url):
    """Replace any scheme in url with the given scheme and return.

    The scheme is not included with a relative file path.
    Arguments:
        scheme -- the new scheme to add
        url -- the address be modified
    """
    oldScheme, drive, address = splitUrl(url)
    if drive:
        drive = '/' + drive
    elif scheme == 'file' and not address.startswith('/'):
        return address
    elif scheme == 'mailto':
        return '{0}:{1}'.format(scheme, address)
    return '{0}://{1}{2}'.format(scheme, drive, address)

def shortName(url):
    """Return a default short name using the base portion of the URL filename.

    Arguments:
        url -- a string with the original URL
    """
    scheme, drive, address = splitUrl(url)
    name = os.path.basename(address)
    if not name:    # remove trailing separator if there is no basename
        name = os.path.basename(address[:-1])
    if scheme == 'mailto' or '@' in name:
        name = name.split('@', 1)[0]
    return name

def isRelative(url):
    """Return true if this URL is a relative path.

    Any scheme or drive letter is considered absolute and returns false.

    Arguments:
        url -- a string with the original URL
    """
    scheme, drive, address = splitUrl(url)
    if scheme or drive or address.startswith('/'):
        return False
    return True

def toAbsolute(url, refPath, addScheme=True):
    """Convert a relative file URL to an absolute URL and return it.

    Arguments:
        url -- a string with the original URL
        refPath -- the path that the URL is relative to
        addScheme -- add the 'file' scheme to result if true
    """
    scheme, drive, address = splitUrl(url)
    url = os.path.normpath(os.path.join(refPath, drive + address))
    if addScheme:
        return replaceScheme('file', url)
    if os.sep == '\\':
        url = url.replace('\\', '/')
    return url

def toRelative(url, refPath):
    """Convert an absolute file URL to a relative URL and return it.

    Arguments:
        url -- a string with the original URL
        refPath -- the path that the URL is relative to
    """
    scheme, drive, address = splitUrl(url)
    if drive or address.startswith('/'):
        try:
            url = os.path.relpath(drive + address, refPath)
        except ValueError:
            pass
    if os.sep == '\\':
        url = url.replace('\\', '/')
    return url

def which(fileName):
    """Return the full path if the fileName is found somewhere in the PATH.

    If not found, return an empty string.
    Similar to the Linux which command.
    Arguments:
        fileName -- the name to search for
    """
    extList = ['']
    if sys.platform.startswith('win'):
        extList.extend(os.getenv('PATHEXT', '').split(os.pathsep))
    for path in os.get_exec_path():
        for ext in extList:
            fullPath = os.path.join(path, fileName + ext)
            if os.access(fullPath, os.X_OK):
                return fullPath
    return ''
