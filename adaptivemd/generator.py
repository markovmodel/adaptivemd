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


from file import File
from mongodb import StorableMixin
import os


class TaskGenerator(StorableMixin):
    """
    A generator helper for `Task` object creation

    This is an important group and is supposed to make it easy for you to
    create `Task` object. In a real situation a user should not be faced
    with the `Task` details, or at least the programming of a generator is
    a separate problem. Once you have the generators use them in your
    adaptive scripts.

    Examples
    --------

    Attributes
    ----------
    initial_staging : list of dict or str or `Action`
        a list of actions to be run once before this generator can be used
    items : dict of `File`
        a dictionary of `File` by name to simplify access to certain files
    """
    def __init__(self):
        super(TaskGenerator, self).__init__()
        self._items = dict()
        self.initial_staging = []

    def __getitem__(self, item):
        return self._items[item]

    def __setitem__(self, key, value):
        self._items[key] = value

    def items(self):
        return self._items.items()

    @classmethod
    def from_dict(cls, dct):
        obj = cls.__new__(cls)
        StorableMixin.__init__(obj)
        obj._items = dct['_items']
        obj.initial_staging = dct['initial_staging']
        return obj

    def to_dict(self):
        return {
            '_items': self._items,
            'initial_staging': self.initial_staging
        }

    @property
    def files(self):
        return {
            key: value
            for key, value in self.items() if isinstance(value, File)}

    @property
    def stage_in(self):
        """
        Return a list of actions needed before tasks can be generated

        Returns
        -------
        list of `Action`
            the list of Actions to be parsed into stage in steps

        """
        return self.initial_staging

    def stage(self, obj, target=None):
        """
        Short cut to add a file to be staged

        Parameters
        ----------
        obj : `File`
            the file to be staged in the initial staging phase
        target : `Location` or str
            the (different) target name to be used

        """
        self.initial_staging.append(
            obj.transfer(target)
        )

rpc_exec = File('file://' + os.path.join(os.path.dirname(__file__), 'scripts/_run_.py')).load()


class PythonRPCTaskGenerator(TaskGenerator):
    """
    A python remote procedure call that executes a python function remotely

    Represents a TaskGenerator that uses the `PythonTask` as a basis. This
    tasks require a special python script to be staged
    """
    def __init__(self):
        super(PythonRPCTaskGenerator, self).__init__()

        self.stage(rpc_exec, 'staging:///')
