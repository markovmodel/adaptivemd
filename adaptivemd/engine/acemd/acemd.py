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


from adaptivemd.task import Task
from adaptivemd.file import Location, File
from adaptivemd.engine import Engine, Frame, Trajectory


class ACEMDEngine(Engine):
    def __init__(self, conf_file, pdb_file, args=None):
        """
        Implementation of the AceMD engine

        Parameters
        ----------
        conf_file : `File`
            reference to the .conf file
        pdb_file : `File`
            reference to a .pdb file
        args : str
            arguments passed to the AceMD command line

        """
        super(ACEMDEngine, self).__init__()

        self._items = dict()

        self['pdb_file'] = pdb_file
        self['conf_file'] = conf_file

        for name, f in self.files.items():
            stage = f.transfer(Location('staging:///'))
            self[name + '_stage'] = stage.target
            self.initial_staging.append(stage)

        if args is None:
            args = ''

        self.args = args

    @property
    def call_format_str(self):
        return 'acemd %s {0}' % self.args

    def run(self, target):
        return None
