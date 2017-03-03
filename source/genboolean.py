#!/usr/bin/env python3

#******************************************************************************
# genboolean.py, provides a class for boolean formating
#
# Copyright (C) 2014, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re


_formatDict = {N_('true'):True, N_('false'):False,
               N_('yes'):True, N_('no'):False}
for key, value in _formatDict.copy().items():
    _formatDict[key[0]] = value
    _formatDict[_(key)] = value
    _formatDict[_(key)[0]] = value

class GenBoolean:
    """Class to store & format boolean values.

    Uses a simple format of <true>/<false>.
    """
    def __init__(self, boolStr='true'):
        """Initialize a GenBoolean object with any format from _formatDict.
        
        Raises ValueError with an inappropriate argument.
        Arguments:
            boolStr -- the string to evaluate
        """
        self.setBool(boolStr)

    def setBool(self, boolStr):
        """Initialize a GenBoolean object with any format from _formatDict.
        
        Raises ValueError with an inappropriate argument.
        Arguments:
            boolStr -- the string to evaluate
        """
        try:
            self.value = _formatDict[boolStr.lower()]
        except KeyError:
            raise ValueError

    def setFromStr(self, boolStr, strFormat='yes/no'):
        """Set boolean value based on given format string.

        Raises ValueError with an inappropriate argument.
        Returns self.
        Arguments:
            boolStr -- the string to evaluate
            strFormat -- a text format in True/False style
        """
        try:
            self.value = self.customFormatDict(strFormat)[boolStr.lower()]
        except KeyError:
            raise ValueError
        return self

    @staticmethod
    def customFormatDict(strFormat):
        """Return a dictionary based on the format.

        The dictionary includes conversions in both directions.
        String keys are in lower case.
        Raises ValueError with an inappropriate format.
        Arguments:
            strFormat -- a text format in True/False style
        """
        trueVal, falseVal = strFormat.split('/', 1)
        if not trueVal or not falseVal or trueVal == falseVal:
            raise ValueError
        return {trueVal.lower():True, falseVal.lower():False,
                True:trueVal, False:falseVal}

    def boolStr(self, strFormat='yes/no'):
        """Return the boolean string in the given strFormat.

        Arguments:
        Format:
            strFormat -- a text format in True/False style
        """
        return self.customFormatDict(strFormat)[self.value]

    def clone(self):
        """Return cloned instance.
        """
        return self.__class__(self.value)

    def __repr__(self):
        """Outputs in general string fomat.
        """
        return repr(self.value)

    def __eq__(self, other):
        """Equality test.
        """
        try:
            return self.value == other.value
        except AttributeError:
            return self.value == other

    def __ne__(self, other):
        """Non-equality test.
        """
        try:
            return self.value != other.value
        except AttributeError:
            return self.value != other

    def __hash__(self):
        """Allow use as dictionary key.
        """
        return hash(self.value)

    def __nonzero(self):
        """Allow truth testing.
        """
        return self.value
