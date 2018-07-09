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

import os
from .mongodb import StorableMixin, SyncVariable
from .task import DummyTask
from .util import parse_cfg_file


# TODO
# Read this guy as function
# and eliminate the (incorrect) use of
# truncated names
#from .rp import rp_resource_list

# Where it came from now:
#from radical.pilot import Session
#s = Session()
#_resource_names = [k.split('_')[0] for k in s._resource_configs.keys()]

# TODO
# **** Want to add ability to grab specific nodes that aren't caught
#      by specifying the queue name
#
# on Rhea:
#           #PBS -lpartition=gpu



class Configuration(StorableMixin):
    """
    Object to store configuration of the execution resource.

    This class is used to pass information about the resource
    when using Radical Pilot, so the field "resource_name" must have a
    matching entry in the Radical Pilot resource configurations. If
    the "shared_path" is not defined, it is set to $HOME/adaptivemd,
    which is likely not a good working a data directory on an HPC.
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
    current : `bool`
        Flag for to signify the configuration is in or selected for use
    cores_per_node : `int`
        Number of cores/threads on each node. This should correspond
        to the specifications of nodes in the requested queues.
    resource_name : `rp.resource`
        A string corresponding to a resource that is defined within
        Radical Pilot

    Methods
    -------
    read_configurations

    """
    _ext = '.cfg'
    _fields = [('shared_path',str), ('queues',str),
               ('allocation',str), ('cores_per_node',int),
               ('resource_name',str), ('current', bool),
               ('gpu_per_node',int)]

    # TODO sync new vals, difficult with current implementation
    #for _field, _type in _fields:
        #setattr(Configuration, _field, SyncVariable(_field, lambda f: isinstance(f, _type)))

    _resource_names = set(['fub.allegro', 'xsede.supermic',
        'das4.fs2', 'osg.connect', 'xsede.stampede',
        'radical.tutorial', 'lumc.gb-ui', 'chameleon.cloud',
        'xsede.trestles', 'osg.xsede-virt-clust',
        'futuregrid.echo', 'nersc.edison', 'xsede.greenfield',
        'xsede.bridges', 'xsede.lonestar', 'futuregrid.bravo',
        'xsede.gordon', 'radical.one', 'xsede.wrangler',
        'stfc.joule', 'futuregrid.delta', 'lumc.shark',
        'ornl.titan_aprun', 'ncar.yellowstone', 'xsede.comet', 'ornl.titan_orte',
        'local.localhost', 'xsede.blacklight', 'yale.grace',
        'rice.davinci', 'lrz.supermuc', 'nersc.hopper',
        'futuregrid.xray', 'iu.bigred2', 'rice.biou',
        'futuregrid.india', 'das5.fs1', 'epsrc.archer',
        'ncsa.bw', 'radical.two', 'xsede.stampede2'])


    def get_resource_list(self):
        # TODO Use this method to get list of resource names
        pass


    # TODO init from passed dict
    def __init__(self, name, wrapper=None, **fields):
        # Configuration initialization will only complete if all
        # entries read from the configuration file entry correspond
        # to valid fields, and the resource name is a known
        # resource configured in Radical Pilot.
        #  - verify this with test...
        # TODO  conditional system that checks rp compatibility of a resource

        # Construction from file
        if fields:
            if 'resource_name' in fields:
                if fields['resource_name'] not in Configuration._resource_names:
                    raise ValueError("Resouce Name is not defined")

            _dict = self.process_attributes(fields)
            super(Configuration, self).__init__()
            [setattr(self, field, val) for field, val in _dict.items()]
            self.name = name

        # Construction via from_dict from storage
        else:
            super(Configuration, self).__init__()

        # TODO add default val to _fields tuples above
        #      and set them here
        unused = filter(lambda f: not hasattr(self, f), zip(*self._fields)[0])
        [setattr(self, uu, None) for uu in unused]

        if self.shared_path is None:
            self.shared_path = '$HOME/adaptivemd/'

        if self.current is None:
            self.current = False

        if not isinstance(self.queues, list):
            self.queues = [self.queues]

        if wrapper is None:
            wrapper = DummyTask()

        self.wrapper = wrapper


    # TODO remove extra filename field project_name
    @classmethod
    def read_configurations(cls, configuration_file='', project_name=None):
        '''
        This method will read resource configurations from the given file

        The method returns a list of `Configuration`
        objects. The key of each configuration dict
        is a given name. The keys in each configuration dict
        are fields read from the configuration file with values
        read from the file.

        See adaptivemd/examples/configurations.txt for an example
        of the format.

        Parameters
        ----------
        configuration_file : `str`
            Path to configuration file
        project_name : `str`
            Name of file to get in cwd

        Returns
        -------
        `list` of `Configuration`
        '''

        f_cfg = None
        configurations = list()

        # TODO replace/upgrade cfg parser to receive
        #      an adaptivemd file object
        configuration_file = os.path.normpath(
            os.path.expandvars(configuration_file)
            )

        # Look in other locations
        if not configuration_file:
            locs = ['./' + project_name + cls._ext,]

            if os.path.isfile(locs[0]):
                f_cfg = locs[0]

        # Use given file
        elif os.path.isfile(configuration_file):
            f_cfg = configuration_file

        # create configuration objects from parsed config
        if f_cfg:
            configurations_fields = parse_cfg_file(f_cfg)

            for configuration, fields in configurations_fields.items():
                configurations.append(cls(configuration, **fields))

        # making configuration for localhost
        elif configuration_file and f_cfg is None:
            print("Could not locate the given configuration file: {0}\n"
                  .format(configuration_file,
                  "Going to use default local configuration"))

            configurations.append(cls('local', **dict(resource_name='local.localhost')))

        else:
            configurations.append(cls('local', **dict(resource_name='local.localhost')))

        return configurations

    @classmethod
    def process_attributes(cls, fields):
        _fields, _types = zip(*cls._fields)
        _dict = dict()
        for field, val in fields.items():
            try:
                idx = _fields.index(field)
                _type = _types[idx]
                _val = _type(val)

                assert isinstance(_val, _type)
                _dict[field] = _val

            except ValueError:
                print("Listed field {0} is not a valid configuration field"
                      .format(field))

            except AssertionError:
                print("Listed field {0} is not the required type {1}"
                      .format(field, _type))

        return _dict

