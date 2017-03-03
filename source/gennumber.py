#!/usr/bin/env python3

#******************************************************************************
# gennumber.py, provides a class for number formating
#
# Copyright (C) 2011, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re
import math


class GenNumber:
    """Class to store & format number values.

    Uses a simple syntax (sequence of '#', '0', etc.) for formatting.
    """
    def __init__(self, num=0):
        """Initialize a GenNumber object with a number, string or a GenNumber.
        
        Raises ValueError with an inappropriate argument.
        Accepts one of the following arguments as num to initialize:
               1. int value
               2. float value
               3. string in common int or float format
               4. GenNumber instance
        """
        self.setNumber(num)

    def setNumber(self, num):
        """Sets the number value from an int, float, string or a GenNumber.
        
        Raises ValueError with an inappropriate argument.
        Arguments:
            num -- the value in int, float, string or GenNumber format
        """
        try:
            self.num = int(str(num))
        except ValueError:
            self.num = float(str(num))

    def setFromStr(self, numStr, strFormat='#\,###'):
        """Set number value based on given format string.

        Removes the extra characters from format and uses format's radix char.
        Returns self.
        Arguments:
            numStr -- the string to evaluate
            strFormat -- the format to use to interpret the number string
        """
        radix = _getRadix(strFormat)
        strFormat = _unescapeFormat(radix, strFormat).strip()
        extraChar = re.sub(r'[#0\seE\-\+{}]'.format(re.escape(radix)), '',
                           strFormat)
        if extraChar:
            numStr = re.sub('[{}]'.format(re.escape(extraChar)), '', numStr)
        if radix == ',':
            numStr = numStr.replace(',', '.')
        self.setNumber(numStr)
        return self

    def numStr(self, strFormat='#.##'):
        """Return the number string in the given format, including exponents.

        Format:
            # = optional digit
            0 = required digit
            e = exponent
            - = optional sign
            + = required sign
            space (external) = digit or space
            space (internal) = thousands sep
            \, = thousands separator
            \. = thousands separator
        Arguments:
            strFormat -- format for number export
        """
        formMain, formExp = _doubleSplit('eE', strFormat)
        if not formExp:
            return self.basicNumStr(strFormat)
        exp = math.floor(math.log10(abs(self.num)))
        num = self.num / 10**exp
        totPlcs = len(re.findall(r'[#0]', formMain))
        num = round(num, totPlcs - 1 if totPlcs > 0 else 0)
        wholePlcs = len(re.findall(r'[#0]', _doubleSplit('.', formMain)[0]))
        expChg = wholePlcs - int(math.floor(math.log10(abs(num)))) - 1
        num = num * 10**expChg
        exp -= expChg
        c = 'e' if 'e' in strFormat else 'E'
        return '{0}{1}{2}'.format(GenNumber(num).basicNumStr(formMain), c,
                               GenNumber(exp).basicNumStr(formExp))

    def basicNumStr(self, strFormat='#.##'):
        """Return number string in the given format, without exponent support.

        Format:
            # = optional digit
            0 = required digit
            - = optional sign
            + = required sign
            space (external) = digit or space
            space (internal) = thousands sep
            \, = thousands separator
            \. = thousands separator
        Arguments:
            strFormat -- format for number export
        """
        radix = _getRadix(strFormat)
        strFormat = _unescapeFormat(radix, strFormat)
        formWhole, formFract = _doubleSplit(radix, strFormat)
        decPlcs = len(re.findall(r'[#0]', formFract))
        numWhole, numFract = _doubleSplit('.', '{0:.{1}f}'.format(self.num,
                                                                  decPlcs))
        numFract = numFract.rstrip('0')
        numWhole, numFract = list(numWhole), list(numFract)
        formWhole, formFract = list(formWhole), list(formFract)
        sign = '+'
        if numWhole[0] == '-':
            sign = numWhole.pop(0)
        result = []
        while numWhole or formWhole:
            c = formWhole.pop() if formWhole else ''
            if c and c not in '#0 +-':
                if numWhole or '0' in formWhole:
                    result.insert(0, c)
            elif numWhole and c != ' ':
                result.insert(0, numWhole.pop())
                if c and c in '+-':
                    formWhole.append(c)
            elif c in '0 ':
                result.insert(0, c)
            elif c in '+-':
                if sign == '-' or c == '+':
                    result.insert(0, sign)
                sign = ''
        if sign == '-':
            if result[0] == ' ':
                result = [re.sub(r'\s(?!\s)', '-', ''.join(result), 1)]
            else:
                result.insert(0, '-')
        if formFract or (strFormat and strFormat[-1] == radix):
            result.append(radix)
        while formFract:
            c = formFract.pop(0)
            if c not in '#0 ':
                if numFract or '0' in formFract:
                    result.append(c)
            elif numFract:
                result.append(numFract.pop(0))
            elif c in '0 ':
                result.append('0')
        return ''.join(result)

    def clone(self):
        """Return cloned instance.
        """
        return self.__class__(self.num)

    def __repr__(self):
        """Outputs in general string fomat.
        """
        return repr(self.num)

    def __eq__(self, other):
        """Equality test.
        """
        try:
            return self.num == other.num
        except AttributeError:
            return self.num == other

    def __ne__(self, other):
        """Non-equality test.
        """
        try:
            return self.num != other.num
        except AttributeError:
            return self.num != other

    def __lt__(self, other):
        """Less than test.
        """
        try:
            return self.num < other.num
        except AttributeError:
            return self.num < other

    def __gt__(self, other):
        """Greater than test.
        """
        try:
            return self.num > other.num
        except AttributeError:
            return self.num > other

    def __le__(self, other):
        """Less than or equal to test.
        """
        try:
            return self.num <= other.num
        except AttributeError:
            return self.num <= other

    def __ge__(self, other):
        """Greater than or equal to test.
        """
        try:
            return self.num >= other.num
        except AttributeError:
            return self.num >= other

    def __add__(self, other):
        """Addition operator.
        """
        try:
            return self.num + other.num
        except AttributeError:
            return self.num + other

    def __radd__(self, other):
        """Reverse addition operator.
        """
        return other + self.num

    def __sub__(self, other):
        """Subtraction operator.
        """
        try:
            return self.num - other.num
        except AttributeError:
            return self.num - other

    def __rsub__(self, other):
        """Reverse subtraction operator.
        """
        return other - self.num

    def __mul__(self, other):
        """Multiplication operator.
        """
        try:
            return self.num * other.num
        except AttributeError:
            return self.num * other

    def __rmul__(self, other):
        """Reverse multiplication operator.
        """
        return other * self.num

    def __truediv__(self, other):
        """True division operator.
        """
        try:
            return self.num / other.num
        except AttributeError:
            return self.num / other

    def __rtruediv__(self, other):
        """Reverse true division operator.
        """
        return other / self.num

    def __floordiv__(self, other):
        """Floor division operator.
        """
        try:
            return self.num // other.num
        except AttributeError:
            return self.num // other

    def __rfloordiv__(self, other):
        """Reverse floor division operator.
        """
        return other // self.num

    def __int__(self):
        """Return integer value.
        """
        return int(self.num)

    def __float__(self):
        """Return float value.
        """
        return float(self.num)

    def __round__(self):
        """Return rounded value.
        """
        return round(self.num)

    def __hash__(self):
        """Allow use as dictionary key.
        """
        return hash(self.num)


######### Utility Functions ##########

def _doubleSplit(sepChars, string):
    """Return tuple of string split in two, separated by one of sepChars.

    Returns a tuple, size 2, with the second entry empty if no sep found.
    Arguments:
        sepChars -- a string of separator characters
        string -- the string to split
    """
    for sep in sepChars:
        result = string.split(sep, 1)
        if len(result) == 2:
            return result
    return (string, '')

def _getRadix(strFormat):
    """Return the radix character (. or ,) used in format.

    Infers from use of slashed separators and non-slashed radix.
    Assumes radix is "." if ambiguous.
    Arguments:
        strFormat -- the string format to evaluate
    """
    if not '\,' in strFormat and ('\.' in strFormat or (',' in strFormat
                                                    and not '.' in strFormat)):
        return ','
    return '.'

def _unescapeFormat(radix, strFormat):
    """Return format with escapes removed from non-radix separators.
    
    Arguments:
        radix -- the current radix character
        strFormat - the string format to modify
    """
    if radix == '.':
        return strFormat.replace('\,', ',')
    return strFormat.replace('\.', '.')
