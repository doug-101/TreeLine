#!/usr/bin/env python3

#******************************************************************************
# matheval.py, provides a safe eval of mathematical expressions
#
# TreeLine, an information storage program
# Copyright (C) 2019, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, either Version 2 or any later
# version.  This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY.  See the included LICENSE file for details.
#******************************************************************************

import re
import ast
import enum
import datetime
import builtins
import fieldformat
import gennumber
from math import *

_nowDateString = 'Now_Date'
_nowTimeString = 'Now_Time'
_nowDateTimeString = 'Now_Date_Time'


def sum(*args):
    """Override the builtin sum function to handle multiple arguments.

    Arguments:
        *args -- lists of numbers or individual numbers
    """
    fullList = []
    for arg in args:
        if hasattr(arg, 'extend'):
            fullList.extend(arg)
        else:
            fullList.append(arg)
    return builtins.sum(fullList)

def max(*args):
    """Override the builtin max function to expand list arguments.

    Arguments:
        *args -- lists of numbers or individual numbers
    """
    fullList = []
    for arg in args:
        if hasattr(arg, 'extend'):
            fullList.extend(arg)
        else:
            fullList.append(arg)
    if not fullList:
        return 0
    return builtins.max(fullList)

def min(*args):
    """Override the builtin min function to expand list arguments.

    Arguments:
        *args -- lists of numbers or individual numbers
    """
    fullList = []
    for arg in args:
        if hasattr(arg, 'extend'):
            fullList.extend(arg)
        else:
            fullList.append(arg)
    if not fullList:
        return 0
    return builtins.min(fullList)

def mean(*args):
    """Added function to calculate the arithmetic average.

    Arguments:
        *args -- lists of numbers or individual numbers
    """
    fullList = []
    for arg in args:
        if hasattr(arg, 'extend'):
            fullList.extend(arg)
        else:
            fullList.append(arg)
    if not fullList:
        return 0
    return builtins.sum(fullList) / len(fullList)

# don't use pow() function from math library
pow = builtins.pow

def startswith(text, firstText):
    """Added compare function, returns true if text starts with firstText.

    Arguments:
        text -- the string to check
        firstText -- the starting text
    """
    return str(text).startswith(str(firstText))

def endswith(text, firstText):
    """Added compare function, returns true if text ends with firstText.

    Arguments:
        text -- the string to check
        firstText -- the ending text
    """
    return str(text).endswith(str(firstText))

def contains(text, innerText):
    """Added compare function, returns true if text contains innerText.

    Arguments:
        text -- the string to check
        innerText -- the inside text
    """
    return str(innerText) in str(text)

def join(sep, *args):
    """Added text function to combine strings.

    Arguments:
        sep -- the separator string
        *args -- lists of strings or individual strings to combine
    """
    fullList = []
    for arg in args:
        if hasattr(arg, 'extend'):
            fullList.extend(arg)
        else:
            fullList.append(arg)
    return sep.join([str(i) for i in fullList if str(i)])

def upper(text):
    """Added text function for upper case.

    Arguments:
        text -- the string to modify
    """
    return str(text).upper()

def lower(text):
    """Added text function for lower case.

    Arguments:
        text -- the string to modify
    """
    return str(text).lower()

def replace(text, oldText, newText):
    """Added text function to replace strings.

    Arguments:
        text -- the string to modify
        oldText -- the string to be replaced
        newText -- the replacement string
    """
    return str(text).replace(str(oldText), str(newText))


_fieldSplitRe = re.compile(r'{\*(\*|\$|&|#|\b)([\w_\-.]+)\*}')

class MathEquation:
    """Class to parse, check, store and evaluate a Math field equation.
    """
    def __init__(self, eqnText=''):
        """Initialize the MathEquation.

        Arguments:
            eqnText -- the text of an equation to be parsed
        """
        self.fieldRefs = []
        self.formattedEqnText = ''
        self.parseEquation(eqnText)

    def equationText(self):
        """Return the text representation of the equation.
        """
        fieldNames = ['{{*{0}{1}*}}'.format(ref.tagPrefix, ref.fieldName) for
                      ref in self.fieldRefs]
        return self.formattedEqnText.format(*fieldNames)

    def validate(self):
        """Check if the equation is valid (or empty).

        Use ones as fake input and use ast to verify legality.
        Raises a ValueError if the equation is not valid.
        """
        if not self.formattedEqnText:
            return
        inputs = [ref.testValue for ref in self.fieldRefs]
        checker = SafeEvalChecker()
        try:
            eqn = self.formattedEqnText.format(*inputs)
        except IndexError:
            raise ValueError(_('Illegal "{}" characters'))
        checker.check(eqn)
        try:
            result = eval(eqn)
            if isinstance(result, list):
                raise TypeError('list result not allowed')
        except NameError as err:
            raise ValueError(err)
        except TypeError as err:
            if 'list' in str(err) and '&' in [ref.tagPrefix for ref in
                                              self.fieldRefs]:
                msg = _('Child references must be combined in a function')
                raise ValueError(msg)
        except ZeroDivisionError:
            pass

    def equationValue(self, eqnNode, zeroValue=0, noMarkup=True):
        """Return a value for the equation in the given node.

        Return None if references are invalid.
        Raise a ValueError for illegal math operations.
        Arguments:
            eqnNode -- the node containing the equation to evaluate
            zeroValue -- the value to use for blanks
            noMarkup -- if true, remove html markup
        """
        zeroBlanks = eqnNode.treeStructureRef().mathZeroBlanks
        inputs = [ref.referenceValue(eqnNode, zeroBlanks, zeroValue, noMarkup)
                  for ref in self.fieldRefs]
        if not zeroBlanks and None in inputs:
            return None
        inputs = [repr(value) for value in inputs]
        eqn = self.formattedEqnText.format(*inputs)
        try:
            return eval(eqn)
        except Exception as err:
            raise ValueError(err)

    def parseEquation(self, eqnText):
        """Replace the stored equation by parsing the given text.

        Creates formatted equation text and a list of field references.
        Arguments:
            eqnText -- the text of an equation to be parsed
        """
        self.fieldRefs = []
        self.formattedEqnText = _fieldSplitRe.sub(self._replFunc, eqnText)

    def _replFunc(self, matchObj):
        """Adds a field ref for each field match from the parser.

        Returns a string format placeholder as the replacement text.
        Arguments:
            matchObj -- the field match object
        """
        fieldRefType = matchObj.group(1)
        fieldRefName = matchObj.group(2)
        fieldRefSelector = {'': EquationFieldRef, '*': EquationParentRef,
                            '$': EquationRootRef, '&': EquationChildRef,
                            '#': EquationChildCountRef}
        fieldRef = fieldRefSelector[fieldRefType](fieldRefName)
        self.fieldRefs.append(fieldRef)
        return '{}'


# recursive equation ref eval directions
EvalDir = enum.IntEnum('EvalDir', 'optional upward downward')


class EquationFieldRef:
    """Class to store and eval individual field references in a Math equation.

    This base class handles references within the same node.
    """
    tagPrefix = ''
    testValue = 1
    evalDirection = EvalDir.optional
    def __init__(self, fieldName):
        """Initialize the field references.

        Arguments:
            fieldName -- the name of the referenced field
        """
        self.fieldName = fieldName
        self.eqnNodeTypeName = ''
        self.eqnFieldName = ''

    def referenceValue(self, eqnNode, zeroBlanks=True, zeroValue=0,
                       noMarkup=True):
        """Return the value of the field referenced in a given node.

        Return None if blank or doesn't exist and not zeroBlanks,
        raise a ValueError if it isn't a number.
        Arguments:
            eqnNode -- the node containing the equation to evaluate
            zeroBlanks -- replace blank fields with zeroValue if True
            zeroValue -- the value to use for blanks
            noMarkup -- if true, remove html markup
        """
        try:
            return (eqnNode.formatRef.fieldDict[self.fieldName].
                    mathValue(eqnNode, zeroBlanks, noMarkup))
        except KeyError:
            if self.fieldName == _nowDateString:
                return (datetime.date.today() -
                        fieldformat.DateField.refDate).days
            elif self.fieldName == _nowTimeString:
                now = datetime.datetime.combine(fieldformat.DateField.refDate,
                                                datetime.datetime.now().time())
                ref = datetime.datetime.combine(fieldformat.DateField.refDate,
                                                fieldformat.TimeField.refTime)
                return (now - ref).seconds
            elif self.fieldName == _nowDateTimeString:
                return (datetime.datetime.now() -
                        fieldformat.DateTimeField.refDateTime).total_seconds()
            return zeroValue if zeroBlanks else None

    def dependentEqnNodes(self, refNode):
        """Return a list of equation node(s) that reference the given node.

        Arguments:
            refNode -- the node containing the referenced field
        """
        if refNode.formatRef.name == self.eqnNodeTypeName:
            return [refNode]
        return []


class EquationParentRef(EquationFieldRef):
    """Class to store and eval parent field references in a Math equation.
    """
    tagPrefix = '*'
    testValue = 1
    evalDirection = EvalDir.downward

    def referenceValue(self, eqnNode, zeroBlanks=True, zeroValue=0,
                       noMarkup=True):
        """Return the parent field value referenced from a given node.

        Return None if blank or doesn't exist and not zeroBlanks,
        raise a ValueError if it isn't a number.
        Arguments:
            eqnNode -- the node containing the equation to evaluate
            zeroBlanks -- replace blank fields with zeroValue if True
            zeroValue -- the value to use for blanks
            noMarkup -- if true, remove html markup
        """
        node = eqnNode.spotByNumber(0).parentSpot.nodeRef
        if not node.formatRef:
            return zeroValue if zeroBlanks else None
        try:
            return (node.formatRef.fieldDict[self.fieldName].
                    mathValue(node, zeroBlanks, noMarkup))
        except KeyError:
            return zeroValue if zeroBlanks else None

    def dependentEqnNodes(self, refNode):
        """Return a list of equation node(s) that reference the given node.

        Arguments:
            refNode -- the node containing the referenced field
        """
        return [node for node in refNode.childList if
                node.formatRef.name == self.eqnNodeTypeName]


class EquationRootRef(EquationFieldRef):
    """Class to store and eval root node field references in a Math equation.
    """
    tagPrefix = '$'
    testValue = 1
    evalDirection = EvalDir.downward

    def referenceValue(self, eqnNode, zeroBlanks=True, zeroValue=0,
                       noMarkup=True):
        """Return the root field value referenced from a given node.

        Return None if blank or doesn't exist and not zeroBlanks,
        raise a ValueError if it isn't a number.
        Arguments:
            eqnNode -- the node containing the equation to evaluate
            zeroBlanks -- replace blank fields with zeroValue if True
            zeroValue -- the value to use for blanks
            noMarkup -- if true, remove html markup
        """
        node = eqnNode.spotByNumber(0).spotChain()[0].nodeRef
        try:
            return (node.formatRef.fieldDict[self.fieldName].
                    mathValue(node, zeroBlanks, noMarkup))
        except KeyError:
            return zeroValue if zeroBlanks else None

    def dependentEqnNodes(self, refNode):
        """Return a list of equation node(s) that reference the given node.

        Arguments:
            refNode -- the node containing the referenced field
        """
        if 1 not in {len(spot.spotChain()) for spot in refNode.spotRefs}:
            # not a root node
            return []
        refs = [node for node in refNode.descendantGen() if
                node.formatRef.name == self.eqnNodeTypeName]
        if refs[0] is refNode:
            refs = refs[1:]
        return refs


class EquationChildRef(EquationFieldRef):
    """Class to store and eval child field references in a Math equation.
    """
    tagPrefix = '&'
    testValue = [1]
    evalDirection = EvalDir.upward

    def referenceValue(self, eqnNode, zeroBlanks=True, zeroValue=0,
                       noMarkup=True):
        """Return a list with child field values referenced from a given node.

        Return None if there are blanks and zeroBlanks is false,
        raise a ValueError if any aren't a number.
        Arguments:
            eqnNode -- the node containing the equation to evaluate
            zeroBlanks -- replace blank fields with zeroValue if True
            zeroValue -- the value to use for blanks
        """
        result = []
        for node in eqnNode.childList:
            try:
                num = (node.formatRef.fieldDict[self.fieldName].
                       mathValue(node, zeroBlanks, noMarkup))
                if num == None:
                    return None
                result.append(num)
            except KeyError:
                if not zeroBlanks:
                    return None
        if not result:
            result = [zeroValue]
        return result

    def dependentEqnNodes(self, refNode):
        """Return a list of equation node(s) that reference the given node.

        Arguments:
            refNode -- the node containing the referenced field
        """
        node = refNode.spotByNumber(0).parentSpot.nodeRef
        if node.formatRef and node.formatRef.name == self.eqnNodeTypeName:
            return [node]
        return []


class EquationChildCountRef(EquationFieldRef):
    """Class to store and eval child count references in a Math equation.
    """
    tagPrefix = '#'
    testValue = 1
    evalDirection = EvalDir.optional

    def referenceValue(self, eqnNode, zeroBlanks=True, zeroValue=0,
                       noMarkup=True):
        """Return the child count referenced from the given node.

        Arguments:
            eqnNode -- the node containing the equation to evaluate
            zeroBlanks -- replace blank fields with zeroValue if True
            zeroValue -- the value to use for blanks
            noMarkup -- if true, remove html markup
        """
        return len(eqnNode.childList)

    def dependentEqnNodes(self, refNode):
        """Return a list of equation node(s) that reference the given node.

        Arguments:
            refNode -- the node containing the referenced field
        """
        node = refNode.spotByNumber(0).parentSpot.nodeRef
        if node and node.formatRef.name == self.eqnNodeTypeName:
            return [node]
        return []


class RecursiveEqnRef:
    """Class to store a references to other equations in a tree structure.

    Resolves sequence and direction of global evaluations.
    """
    recursiveRefDict = {}
    def __init__(self, eqnTypeName, eqnField):
        """Initialize the RecursiveEquationRef.

        Arguments:
            eqnTypeName -- the type format name contining the equation field
            eqnField -- the field with the equation to eval for other eqn refs
        """
        self.eqnTypeName = eqnTypeName
        self.eqnField = eqnField
        self.evalSequence = 0
        self.evalDirection = EvalDir.optional

    def setPriorities(self, visitedFields=None):
        """Recursively set sequence and direction for evaluation.

        Arguments:
            visitedFields -- set of used eqn field names to check circular refs
        """
        if self.evalSequence != 0:
            return
        if visitedFields == None:
            visitedFields = set()
        visitedFields = visitedFields.copy()
        visitedFields.add(self.eqnField.name)
        self.evalSequence = 1
        for fieldRef in self.eqnField.equation.fieldRefs:
            if (fieldRef.fieldName in visitedFields and
                fieldRef.tagPrefix != '#' and
                (self.eqnField.name != fieldRef.fieldName or
                 fieldRef.evalDirection == EvalDir.optional)):
                raise CircularMathError()
            for eqnRef in self.recursiveRefDict.get(fieldRef.fieldName, []):
                eqnRef.setPriorities(visitedFields)
                if eqnRef.evalSequence >= self.evalSequence:
                    self.evalDirection = fieldRef.evalDirection
                    self.evalSequence = eqnRef.evalSequence
                    if (self.evalDirection != eqnRef.evalDirection or
                        self.evalDirection == EvalDir.optional):
                        self.evalSequence += 1

    def __lt__(self, other):
        """Use sequence and direction as comparison keys for sorting.

        Arguments:
            other -- the equation ref to compare
        """
        return ((self.evalSequence, self.evalDirection) <
                (other.evalSequence, other.evalDirection))


class CircularMathError(Exception):
    """Exception raised when circular references are found in math fields.
    """
    pass


allowedFunctions = set(['abs', 'float', 'int', 'len', 'max', 'min', 'pow',
                        'round', 'sum', 'mean',
                        'ceil', 'fabs', 'factorial', 'floor', 'fmod', 'fsum',
                        'trunc', 'exp', 'log', 'log10', 'pow', 'sqrt',
                        'acos', 'asin', 'atan', 'cos', 'sin', 'tan', 'hypot',
                        'degrees', 'radians', 'pi', 'e',
                        'startswith', 'endswith', 'contains',
                        'join', 'upper', 'lower', 'replace'])

allowedNodeTypes = set(['Module', 'Expr', 'Name', 'NameConstant', 'Constant',
                        'Load', 'IfExp', 'Compare', 'Num', 'Str', 'Tuple',
                        'List', 'BinOp', 'UnaryOp', 'Add', 'Sub', 'Mult',
                        'Div', 'Mod', 'Pow', 'FloorDiv', 'Invert', 'Not',
                        'UAdd', 'USub', 'Eq', 'NotEq', 'Lt', 'LtE', 'Gt',
                        'GtE', 'Is', 'IsNot', 'In', 'NotIn', 'BoolOp',
                        'And', 'Or'])


class SafeEvalChecker(ast.NodeVisitor):
    """Class to check that only safe functions are used in an eval expression.

    Raises a ValueError if unsafe or non-numeric operations are present.
    Ref. stackoverflow.com questions 10661079 and 12523516
    """

    def check(self, expr):
        """Check the given expression for non-numeric operations.

        Arguments:
            expr -- the expression string to check
        """
        try:
            tree = ast.parse(expr)
        except SyntaxError:
            raise ValueError(_('Illegal syntax in equation'))
        self.visit(tree)

    def visit_Call(self, node):
        """Check for allowed functions only.

        Arguments:
            node -- the ast node being checked
        """
        if node.func.id in allowedFunctions:
            super().generic_visit(node)
        else:
            raise ValueError(_('Illegal function present: {0}').
                             format(node.func.id))

    def generic_visit(self, node):
        """Check for allowed node types and operators.

        Arguments:
            node -- the ast node being checked
        """
        if type(node).__name__ in allowedNodeTypes:
            super().generic_visit(node)
        else:
            raise ValueError(_('Illegal object type or operator: {0}').
                             format(type(node).__name__))


if __name__ == '__main__':
    checker = SafeEvalChecker()
    try:
        print('Enter expression: ')
        expr = input()
        checker.check(expr)
    except ValueError as err:
        print(err)
    else:
        print(eval(expr))
