##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: Jan-Hendrik Prinz
#          John Ossyra
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
from __future__ import absolute_import


from .mongodb import StorableMixin
#from .task import DummyTask
from .configuration import Configuration


class Resource(StorableMixin):
    """
    Runtime parameters to specify execution resources

    queue <str> :
        name of the queue to submit jobs to

    total_cpus <int> :
        total number of nodes to be used

    total_time <int> :
        total number of minutes for execution of a block of tasks

    """

    def __init__(self, total_cpus, total_time,
                 total_gpus, destination=None):#, name):

        super(Resource, self).__init__()

        #assert isinstance(name, str)
        #self.name = name

        assert isinstance(total_cpus, int)
        self.total_cpus = total_cpus

        assert isinstance(total_cpus, int)
        self.total_time = total_time

        assert isinstance(total_gpus, int)
        self.total_gpus = total_gpus

        if destination is None:
            destination = ''

        assert isinstance(destination, str)
        self.destination = destination


#del#    def __init__(self, shared_path=None, wrapper=None):
#del#        super(Resource, self).__init__()
#del#        if shared_path is None:
#del#            shared_path = '$HOME/adaptivemd/'
#del#
#del#        self.shared_path = shared_path
#del#        if wrapper is None:
#del#            wrapper = DummyTask()
#del#
#del#        self.wrapper = wrapper


#update#class AllegroCluster(Resource):
#update#    """
#update#    The FUB Allegro cluster and its queues with shared FS on ``NO_BACKUP``
#update#
#update#    """
#update#    def __init__(self, shared_path=None):
#update#        if shared_path is None:
#update#            shared_path = '$HOME/NO_BACKUP/adaptivemd/'
#update#
#update#        super(AllegroCluster, self).__init__(shared_path=shared_path)
#update#
#update#    def add_cuda_module(self):
#update#        """
#update#        Add loading the CUDA module
#update#
#update#        """
#update#        w = self.wrapper
#update#        w.pre.append(
#update#            'export MODULEPATH=/import/ag_cmb/software/modules:$MODULEPATH')
#update#        w.pre.append('module load cuda/7.5')


#update#class LocalResource(Resource):
#update#    """
#update#    Run tasks locally and store data in ``$HOME/adaptivemd/``
#update#    or a directory given by "shared_path"
#update#
#update#    """
#update#    def __init__(self, shared_path=None):
#update#        super(LocalResource, self).__init__(shared_path=shared_path)
#update#
