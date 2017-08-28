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
from __future__ import absolute_import, print_function


from .mongodb import StorableMixin

# Wait until Andre provides a list without having
# to instantiate session
#from .rp import rp_resource_list

# Where it came from now:
#from radical.pilot import Session
#s = Session()
#resource_names = [k.split('_')[0] for k in s._resource_configs.keys()]
resource_names = set(['fub.allegro', 'xsede.supermic', 'das4.fs2', 'osg.connect', 'xsede.stampede', 'radical.tutorial', 'lumc.gb-ui', 'chameleon.cloud', 'xsede.trestles', 'osg.xsede-virt-clust', 'futuregrid.echo', 'nersc.edison', 'xsede.greenfield', 'xsede.bridges', 'xsede.lonestar', 'futuregrid.bravo', 'xsede.gordon', 'radical.one', 'xsede.wrangler', 'stfc.joule', 'futuregrid.delta', 'lumc.shark', 'ornl.titan', 'ncar.yellowstone', 'xsede.comet', 'local.localhost', 'xsede.blacklight', 'yale.grace', 'rice.davinci', 'lrz.supermuc', 'nersc.hopper', 'futuregrid.xray', 'iu.bigred2', 'rice.biou', 'futuregrid.india', 'das5.fs1', 'epsrc.archer', 'ncsa.bw', 'radical.two', 'xsede.stampede2'])



class Configuration(StorableMixin):
    """
    Representation of the filesystem and allocation used to run
    an AdaptiveMD workflow.

    Notes
    -----
    Configurations can be read from a file. Example format is given in
    adaptivemd/examples/configuration.txt. The path must be given to
    the configuration object upon instantiation, or the file can be
    named project_name.cfg and located in the working directory of the
    python session. ie if you are running a project named
    "fun_project", the Configuration object will look for a file
    "fun_project.cfg" to read.

    The configurations file can pack multiple entries into the fields
    'queue' and 'cores_per_node'. If there is more than 1 queue listed,
    the number of 'cores_per_node' either needs to be 1 or match the
    number of queues. Likewise for the opposite case.

    Attributes
    ----------
    name : `str`
        Unique identifier for the particular configuration object

    shared_path : `str`
        Path to use as data storage and working directory home
        on the execution resource

    queue : `str`
        String specifying the queue name to use for
        execution of tasks on a resource

    allocation : `str`
        If required, name of the account to be charged for task execution

    cores_per_node : `int`
        Number of cores/threads on each node. This should correspond
        to the specifications of nodes in the requested queues.

    resource_name : `rp.resource`
        A string corresponding to a resource that is defined within
        Radical Pilot

    """

    # **** Want to add ability to grab specific nodes that aren't caught
    #      by specifying the queue name!!
    #
    # on Rhea:
    #           #PBS -lpartition=gpu

    def read_configuration(configuration_file):
        pass

    def __init__(self, name, shared_path='',
                 queue='', allocation='',
                 cores_per_node=1, resource_name=''):

        if resource_name not in resource_names:
            print("There is no configuration available for resource named:", name)

        else:
            assert isinstance(name, str)
            self.name = name

            assert isinstance(queue, str)
            self.queue = queue

            if not shared_path:
                shared_path = '$HOME/adaptivemd/'
            assert isinstance(shared_path, str)
            self.shared_path = shared_path

            assert isinstance(allocation, str)
            self.allocation = allocation

            assert isinstance(cores_per_node, int)
            self.cores_per_node = cores_per_node

            assert isinstance(resource_name, str)
            self.resource_name = resource_name

            super(Configuration, self).__init__()


