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


class Resource(StorableMixin):
    """
    Runtime parameters to specify execution resources

    Attributes
    ----------
    queue : `str`
        name of the queue to submit jobs to

    total_cpus : `int`
        total number of nodes to be used

    total_time : `int`
        total number of minutes for execution of a block of tasks

    """

    def __init__(self, total_time, total_nodes,
                 total_cpus=None, total_gpus=None, destination=""):#, name):

        super(Resource, self).__init__()

        #assert isinstance(name, str)
        #self.name = name

        assert isinstance(total_time, int)
        self.total_time = total_time

        assert isinstance(total_nodes, int)
        self.total_nodes = total_nodes

        if total_cpus:
            assert isinstance(total_cpus, int)
            self.total_cpus = total_cpus

        if total_gpus:
            assert isinstance(total_gpus, int)
            self.total_gpus = total_gpus

        if destination:
            assert isinstance(destination, str)
            self.destination = destination

