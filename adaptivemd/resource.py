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
from __future__ import absolute_import, print_function


from .mongodb import StorableMixin
from .task import DummyTask


class Resource(StorableMixin):
    """
    Representation of a shared FS with attached execution resources

    """

    def __init__(self, shared_path=None, wrapper=None):
        super(Resource, self).__init__()
        if shared_path is None:
            shared_path = '$HOME/adaptivemd/'

        self.shared_path = shared_path
        if wrapper is None:
            wrapper = DummyTask()

        self.wrapper = wrapper


class AllegroCluster(Resource):
    """
    The FUB Allegro cluster and its queues with shared FS on ``NO_BACKUP``

    """
    def __init__(self, shared_path=None):
        if shared_path is None:
            shared_path = '$HOME/NO_BACKUP/adaptivemd/'

        super(AllegroCluster, self).__init__(shared_path=shared_path)

    def add_cuda_module(self):
        """
        Add loading the CUDA module

        """
        w = self.wrapper
        w.pre.append(
            'export MODULEPATH=/import/ag_cmb/software/modules:$MODULEPATH')
        w.pre.append('module load cuda/7.5')


class LocalResource(Resource):
    """
    Run tasks locally and store results in ``$HOME/adaptivemd/``

    """
    pass
