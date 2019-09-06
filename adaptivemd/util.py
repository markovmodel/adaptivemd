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

#import pip
import pkg_resources
import os
import datetime


_save_logs = bool(os.environ.get("ADMD_SAVELOGS", False))

def get_logger(logname, save_log=False):

    import logging

    _loglevel = os.environ.get('ADMD_LOGLEVEL',"WARNING")

    try:
        if _loglevel.lower() == 'info':
            loglevel = logging.INFO
        elif _loglevel.lower() == 'debug':
            loglevel = logging.DEBUG
        elif _loglevel.lower() == 'warning':
            loglevel = logging.WARNING
        elif _loglevel.lower() == 'error':
            loglevel = logging.ERROR
        # catch attempted set values as WARNING level
        elif isinstance(_loglevel, str):
            loglevel = logging.WARNING
        else:
            loglevel = logging.WARNING

    # catch None's for not set
    except:
        loglevel = logging.WARNING

    formatter = logging.Formatter(
        fmt="[ %(asctime)s.%(msecs)05d ] %(name)s :: %(levelname)s :: %(lineno)d ||  %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    logging.basicConfig(level=loglevel)#, format=formatter)
    logger  = logging.getLogger(logname)

    ch = logging.StreamHandler()
    #ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(loglevel)
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    if save_log or _save_logs:
        logfile = logname + '.log'

        if logfile.startswith("__main__"):
            logfile = "adaptivemd." + logfile

        fh = logging.FileHandler(logfile)
        fh.setLevel(loglevel)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.propagate = False

    return logger


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
    #installed_packages = pip.get_installed_distributions()
    installed_packages = [d for d in pkg_resources.working_set]
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
