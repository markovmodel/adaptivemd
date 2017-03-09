import pip
import os
import datetime


def strip_type(s):
    return s.split('://')[-1]


def get_type(s):
    parts = s.split('://')
    if len(parts) > 1:
        return parts[0]
    else:
        return 'worker'

path_conda_local_sheep = '/home/mi/jprinz/anaconda2/bin'
path_conda_local_jhp = '/Users/jan-hendrikprinz/anaconda/bin/'
path_conda_allegro_jhp = '/home/jprinz/miniconda2/bin/'


def get_function_source(func):
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
