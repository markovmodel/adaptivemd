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

from .mongodb import StorableMixin
from .util import DT


class LogEntry(StorableMixin):
    """
    A storable representation of a log entry

    Examples
    --------
    >>> from adaptivemd import Project
    >>> p = Project('tutorial-project')
    >>> l = LogEntry('worker', 'failed execution', 'simsalabim, didnt work')
    >>> print(l) # doctest: +SKIP
    >>> p.logs.add(l)

    Attributes
    ----------
    logger : str
        the name of the logger for classification
    title : str
        a short title for the log entry
    message : str
        the long and detailed message
    level : int
        pick `LogEntry.SEVERE`, `LogEntry.ERROR` or `LogEntry.INFO` (default)
    objs : dict of storable objects
        you can attach objects that can help with specifying the error message
    """

    SEVERE = 1
    ERROR = 2
    INFO = 3

    def __init__(self, logger, title, message, level=INFO, objs=None):
        super(LogEntry, self).__init__()
        self.logger = logger
        self.title = title
        self.message = message
        self.level = level
        self.objs = objs

    def __str__(self):
        return '%s [%s:%s] %s\n%s' % (
            DT(self.__time__).time,
            self.logger,
            self.level,
            self.title,
            self.message
        )
