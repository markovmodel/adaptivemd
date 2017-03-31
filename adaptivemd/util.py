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


import pip
import os
import datetime


def get_function_source(func):
    """
    Determine the source file of a function

    Parameters
    ----------
    func : function

    Returns
    -------
    str
        the module name
    list of str
        a list of filenames necessary to be copied

    """
    installed_packages = pip.get_installed_distributions()
    inpip = func.__module__.split('.')[0] in [p.key for p in installed_packages]
    insubdir = os.path.realpath(
        func.__code__.co_filename).startswith(os.path.realpath(os.getcwd()))
    is_local = not inpip and insubdir

    if not is_local:
        return func.__module__, []
    else:
        return func.__module__.split('.')[-1], \
               [os.path.realpath(func.__code__.co_filename)]


class DT(object):
    """
    Helper class to convert timestamps to human readable output

    """

    default_format = "%Y-%m-%d %H:%M:%S"

    def __init__(self, stamp):
        if stamp is None:
            self._dt = None
        else:
            self._dt = datetime.datetime.fromtimestamp(stamp)

    def format(self, fmt=None):
        if self._dt is None:
            return '(unset)'

        if fmt is None:
            fmt = self.default_format

        return self._dt.strftime(format=fmt)

    def __repr__(self):
        return self.format()

    def __str__(self):
        return self.format()

    @property
    def date(self):
        return self.format('%Y-%m-%d')

    @property
    def time(self):
        return self.format('%H:%M:%S')

    @property
    def length(self):
        td = self._dt - datetime.datetime.fromtimestamp(0)
        s = '%2d-%02d:%02d:%02d' % (
            td.days, td.seconds / 3600, (td.seconds / 60) % 60, td.seconds % 60)
        return s

    @property
    def ago(self):
        td = datetime.datetime.now() - self._dt
        s = '%2d-%02d:%02d:%02d' % (
            td.days, td.seconds / 3600, (td.seconds / 60) % 60, td.seconds % 60)
        return s
