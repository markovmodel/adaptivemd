##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: Jan-Hendrik Prinz
# Contributors:
#
# `adaptiveMD` is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with MDTraj. If not, see <http://www.gnu.org/licenses/>.
##############################################################################
from __future__ import print_function, absolute_import


class Condition(object):
    """
    A function that returns a bool

    It uses some caching to keep checking fast and allows basic bool operations

    This is really just to replace some simple lambda functions, nothing more.
    It is kind of deprecated and raraly used.

    Examples
    --------
    >>> a = Never()  # never fulfilles
    >>> 'fulfilled' if a else 'not fulfilled'
    'not fulfilled'
    >>> b = Now()  # always fulfilled
    >>> 'fulfilled' if b else 'not fulfilled'
    'fulfilled'
    >>> bool(a & b)
    False
    >>> bool(a | b)
    True
    >>> not a
    True

    """
    def __init__(self):
        self._met = None

    def __call__(self):
        if self._met is None:
            if self.check():
                self._met = True
            else:
                return False

        return self._met

    def check(self):
        return True

    # implement limited set of logic operations

    def __or__(self, other):
        return OrCondition(self, other)

    def __and__(self, other):
        return AndCondition(self, other)

    def __invert__(self):
        return InvertCondition(self)

    def __bool__(self):
        return self()


class InvertCondition(Condition):
    def __init__(self, condition):
        super(InvertCondition, self).__init__()
        self.condition = condition

    def __call__(self):
        return not self.condition()


class AndCondition(Condition):
    def __init__(self, condition1, condition2):
        super(AndCondition, self).__init__()
        self.condition1 = condition1
        self.condition2 = condition2

    def __call__(self,):
        return self.condition1() and self.condition2()


class OrCondition(Condition):
    def __init__(self, condition1, condition2):
        super(OrCondition, self).__init__()
        self.condition1 = condition1
        self.condition2 = condition2

    def __call__(self,):
        return self.condition1() or self.condition2()


class Now(Condition):
    """
    The always True condition
    """
    def __init__(self):
        super(Now, self).__init__()
        self.active = True

    def check(self):
        return True


class Never(Condition):
    """
    The never True condition
    """
    def __init__(self):
        super(Never, self).__init__()
        self.active = True

    def check(self):
        return False


class ConditionList(list):
    """
    A list of `Condition` or functions -> bool

    Behaves exactly like a list and add some convenience function and mapping
    """

    def is_done(self):
        return all([x() for x in self])

