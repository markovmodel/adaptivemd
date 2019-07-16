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
import yaml

from .mongodb import StorableMixin, SyncVariable
from .task import DummyTask


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
    _fields = {'shared_path'   : (str, '$HOME'),
               'resource_name' : (str, 'local.localhost'),
               'queues'        : (str, ''),
               'allocation'    : (str, ''),
               'cores_per_node': (int, 1),
               'gpu_per_node'  : (int, 0),
               'current'       : (bool,False),
              }

    # TODO init from passed dict
    def __init__(self, name, wrapper=None, **fields):
        # Configuration initialization will only complete if all
        # entries read from the configuration file entry correspond
        # to valid fields, and the resource name is a known
        # resource configured in Radical Pilot.
        #  - verify this with test...

        # Construction from file
        if fields:

            _dict = self.process_attributes(fields)
            super(Configuration, self).__init__()

            [setattr(self, field, val) for field, val in _dict.items()]

            self.name = name

            # currently only handle 1 given queue
            # but must convert to list for RP
            if not isinstance(self.queues, list):
                self.queues = [self.queues]

        # Construction via from_dict from storage
        else:
            super(Configuration, self).__init__()

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

        # Use given file
        if os.path.isfile(configuration_file):
            f_cfg = configuration_file

        else:
            # Need to recieve valid, existing config filename
            raise Exception

        # create configuration objects from parsed config
        if f_cfg:
            with open(f_cfg, 'r') as f_yaml:
                configurations_fields = yaml.safe_load(f_yaml)

            for configuration, fields in configurations_fields.items():
                configurations.append(cls(configuration, **fields))

        # making configuration for localhost
        elif configuration_file and f_cfg is None:
            print("Could not locate the given configuration file: {0}\n"
                  .format(configuration_file,
                  "Going to use default local configuration")
            )

            configurations.append(cls('local', **dict(resource_name='local.localhost')))

        else:
            configurations.append(cls('local', **dict(resource_name='local.localhost')))

        return configurations

    @classmethod
    def process_attributes(cls, fields):
        _dict = dict()

        for field, val in fields.items():

            try:
                _type = cls._fields[field][0]
                _val  = _type(val)

                assert isinstance(_val, _type)
                _dict[field] = _val

            except ValueError:
                print("Listed field {0} is not a valid configuration field"
                      .format(field))

            except AssertionError:
                print("Listed field {0} is not the required type {1}"
                      .format(field, _type))

        unused = filter(lambda f: f not in _dict, cls._fields)
        [_dict.update({uu: cls._fields[uu][1]}) for uu in unused]

        return _dict

