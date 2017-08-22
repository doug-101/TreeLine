#!/usr/bin/env python3

#******************************************************************************
# numbering.py, provides classes to format node numbering
#
# TreeLine, an information storage program
# Copyright (C) 2013, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************


import re


class NumberingGroup:
    """Class to store a multi-level numbering format and apply it.
    """
    def __init__(self, numFormat=''):
        """Initialize a multi-level numbering format.

        Arguments:
            numFormat -- a string describing the format
        """
        self.basicFormats = []
        self.sectionStyle = False
        if numFormat:
            self.setFormat(numFormat)

    def setFormat(self, numFormat):
        """Set a new number format.

        Arguments:
            numFormat -- a string describing the format
        """
        self.sectionStyle = False
        formats = _splitText(numFormat.replace('..', '.'), '/')
        if len(formats) < 2:
            formats = _splitText(numFormat.replace('//', '/'), '.')
            if len(formats) > 1:
                self.sectionStyle = True
        self.basicFormats = [BasicNumbering(numFormat) for numFormat in
                             formats]

    def numString(self, inputNumStr):
        """Return a number string for the given level and input.

        The current numbering level is the segment length of the input.
        Raises ValueError on a bad input string.
        Arguments:
            inputNumStr -- a dot-separated string of integers
        """
        if not inputNumStr:
            return ''
        inputNums = [int(num) for num in inputNumStr.split('.')]
        if self.sectionStyle:
            basicFormats = self.basicFormats[:]
            if len(basicFormats) < len(inputNums):
                basicFormats.extend([basicFormats[-1]] * (len(inputNums) -
                                                          len(basicFormats)))
            results = [basicFormat.numString(num) for basicFormat, num in
                       zip(basicFormats, inputNums)]
            return '.'.join(results)
        else:
            level = len(inputNums) - 1
            try:
                basicFormat = self.basicFormats[level]
            except IndexError:
                basicFormat = self.basicFormats[-1]
            return basicFormat.numString(inputNums[level])


_formatRegEx = re.compile(r'(.*)([1AaIi])(.*)')


class BasicNumbering:
    """Class to store an individaul numbering format and apply it.
    """
    def __init__(self, numFormat=''):
        """Initialize a basic numbering format.

        Arguments:
            numFormat -- a string describing the format
        """
        self.numFunction = _stringFromNum
        self.upperCase = True
        self.prefix = ''
        self.suffix = ''
        if numFormat:
            self.setFormat(numFormat)

    def setFormat(self, numFormat):
        """Set a new number format.

        Arguments:
            numFormat -- a string describing the format
        """
        match = _formatRegEx.match(numFormat)
        if match:
            self.prefix, series, self.suffix = match.groups()
            if series == '1':
                self.numFunction = _stringFromNum
            elif series in 'Aa':
                self.numFunction = _alphaFromNum
            else:
                self.numFunction = _romanFromNum
            self.upperCase = series.isupper()
        else:
            self.prefix = numFormat
            self.numFunction = _stringFromNum

    def numString(self, num):
        """Return a number string for the given integer.

        Arguments:
            num -- the integer to convert
        """
        return '{0}{1}{2}'.format(self.prefix,
                                  self.numFunction(num, self.upperCase),
                                  self.suffix)


def _stringFromNum(num, case=None):
    """Return a number string from an integer.

    Arguments:
        num -- the integer to convert
        case -- an unused placeholder
    """
    if num > 0:
        return repr(num)
    return ''

def _alphaFromNum(num, upperCase=True):
    """Return an alphabetic string from an integer.

    Arguments:
        num -- the integer to convert
        upperCase -- return an upper case string if true
    """
    if num <= 0:
        return ''
    result = ''
    while num:
        digit = (num - 1) % 26
        result = chr(digit + ord('A')) + result
        num = (num - digit - 1) // 26
    if not upperCase:
        result = result.lower()
    return result

_romanDict = {0: '', 1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
              7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 20: 'XX', 30: 'XXX',
              40: 'XL', 50: 'L', 60: 'LX', 70: 'LXX', 80: 'LXXX',
              90: 'XC', 100: 'C', 200: 'CC', 300: 'CCC', 400: 'CD',
              500: 'D', 600: 'DC', 700: 'DCC', 800: 'DCCC', 900: 'CM',
              1000: 'M', 2000: 'MM', 3000: 'MMM'}

def _romanFromNum(num, upperCase=True):
    """Return a roman numeral string from an integer.

    Arguments:
        num -- the integer to convert
        upperCase -- return an upper case string if true
    """
    if num <= 0 or num >= 4000:
        return ''
    result = ''
    factor = 1000
    while num:
        digit = num - (num % factor)
        result += _romanDict[digit]
        factor = factor // 10
        num -= digit
    if not upperCase:
        result = result.lower()
    return result

def _splitText(textStr, delimitChar):
    """Split text using the given delimitter and return a list.

    Double delimitters are not split and empty parts are ignored.
    Arguments:
        textStr -- the text to split
        delimitChar -- the delimitter
    """
    result = []
    textStr = textStr.replace(delimitChar * 2, '\0')
    for text in textStr.split(delimitChar):
        text = text.replace('\0', delimitChar)
        if text:
            result.append(text)
    return result
