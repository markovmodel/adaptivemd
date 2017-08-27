##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: John Ossyra
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

def read_configuration(configuration_file):
    pass

class Configuration(StorableMixin):
    """
    Representation of the filesystem and allocation used to run
    an AdaptiveMD workflow.

    """

    # **** Want to add ability to grab specific nodes that aren't caught
    #      by specifying the queue name!!
    #
    # on Rhea:
    #           #PBS -lpartition=gpu

    def __init__(self, name, shared_path=None,
                 queues=[], allocation=None,
                 cores_per_node=1, resource_name=None):

        super(Configuration, self).__init__()

        assert isinstance(name, str)
        self.name = name

        assert isinstance(queues, list)
        for q in queues:
            assert isinstance(q, str)

        self.queues = queues

        if shared_path is None:
            shared_path = '$HOME/adaptivemd/'

        assert isinstance(shared_path, str)
        self.shared_path = shared_path

        if allocation is None:
            allocation = ''

        assert isinstance(allocation, str)
        self.allocation = allocation

        assert isinstance(cores_per_node, int)
        self.cores_per_node = cores_per_node

        if resource_name is None:
            resource_name = ''

        assert isinstance(resource_name, str)
        self.resource_name = resource_name
