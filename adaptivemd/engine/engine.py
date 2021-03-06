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


# Create compute units for various simulation tools
import random
import os

import six

from adaptivemd.file import File
from adaptivemd.generator import TaskGenerator
from adaptivemd.mongodb import StorableMixin, ObjectSyncVariable
#from adaptivemd.task import Task
from adaptivemd.task import PrePostTask


class Engine(TaskGenerator):
    """
    An generator for trajectory simulation tasks

    """

    def __init__(self):
        super(Engine, self).__init__()

        self.types = {}

        # set default output type if nothing is specified
        self.add_output_type('master', 'output.dcd', 1)

    @classmethod
    def from_dict(cls, dct):
        obj = super(Engine, cls).from_dict(dct)
        obj.types = dct['types']
        return obj

    def to_dict(self):
        dct = super(Engine, self).to_dict()
        dct.update({
            'types': self.types})
        return dct

    def run(self, target):
        """
        Create a task that returns a trajectory given in the input

        This method should be implemented in subclasses that implement
        `Engine` functionality for specific MD programs.

        Parameters
        ----------
        target : `Trajectory`
            location of the created target trajectory

        Returns
        -------
        `Task`
            the task object containing the job description

        """
        return None

    def extend(self, target, length):
        """
        Create a task that extends a trajectory given in the input

        Parameters
        ----------
        target : `Trajectory`
            location of the target trajectory to be extended
        length : int
            number of additional frames to be computed

        Returns
        -------
        `Task`
            the task object containing the job description

        """
        return None

    # def file_generators(self):
    #     """
    #     Return a list of function to be run with certain classes
    #
    #     `Trajectory` is a natural object of engine and giving a trajectory including its
    #     initial frame and length is enough to tell the `Engine` on what to generate. Since
    #     this is enough we can define that using a `Trajectory` object in `Scheduler.submit`
    #     will result in a simulation task.
    #
    #     Returns
    #     -------
    #     dict of `type`: function
    #         the dict describing with function to run with which object type
    #
    #     """
    #     return {
    #         Trajectory: self.run
    #     }

    def add_output_type(self, name, filename=None, stride=1, selection=None):
        """
        Add an output type for a trajectory kind to be generated by this engine

        Parameters
        ----------
        name : str
            the name to call the output type by
        filename : str
            a filename to be used for this output type
        stride : int
            the stride used by this particular trajectory relative to the
            native steps of the engine.
        selection : str
            an mdtraj.Topology.select type filter string to store only a subset
            of atoms

        """
        self.types[name] = OutputTypeDescription(filename, stride, selection)

    @property
    def native_stride(self):
        """
        The least common multiple stride of all generated trajectories.

        If you want consistent trajectory length your simulation length need to be
        multiples of this number. The number is relative to the native time steps

        Returns
        -------
        int
            the lcm stride relative to the engines timesteps

        """
        return lcmm(*[x.stride for x in self.types.values()])

    @property
    def full_strides(self):
        """
        list of strides for trajectories that have full coordinates

        this is useful to figure out from which frames you can restart a new
        trajectory. Usually you only have a single one with full frames.

        Returns
        -------
        list of int
            the list of strides for full trajectories

        """
        return [x.stride for x in self.types.values() if x.selection is None]


def gcd(a, b):
    """
    Return greatest common divisor using Euclid's Algorithm.
    """
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """
    Return lowest common multiple.
    """
    return a * b // gcd(a, b)


def lcmm(*args):
    """
    Return lcm of args.
    """
    from functools import reduce
    return reduce(lcm, args)


# ------------------------------------------------------------------------------
# FILE TYPES
# ------------------------------------------------------------------------------

class Trajectory(File):
    """
    Represents a trajectory :class:`File` on the cluster

    Attributes
    ----------
    location : str or `File`
        the `File` location
    frame : `Frame` or `File`
        the initial frame used for the trajectory
    length : int
        the length of the trajectory in frames
    engine : `Engine`
        the engine used to create the trajectory

    """

    _find_by = ['created', 'state', 'task', 'engine']

    engine = ObjectSyncVariable('engine', 'generators', lambda x: not bool(x))

    def __init__(self, location, frame, length, engine=None):
        super(Trajectory, self).__init__(location)

        self.frame = frame
        self.length = length
        self.engine = engine

    def clone(self):
        return Trajectory(self.location, self.frame, self.length, self.engine)

    def __len__(self):
        return self.length

    def __getitem__(self, item):
        if 0 <= item <= len(self):
            return Frame(self, item)
        else:
            return None

    def __repr__(self):
        return "Trajectory(%r >> %s[0..%d])" % (
            self.frame, self.basename, self.length)

    def pick(self):
        """
        Return a random frame from all possible full frames

        Returns
        -------
        `Frame`
            the frame you can restart from

        """
        # only use existing frames (strides!)
        frames = self.existing_frames
        idx = random.randint(0, len(frames) - 1)
        return self[frames[idx]]

    @property
    def is_folder(self):
        # we treat trajectories from now on as Directories
        return True

    def file(self, f):
        """
        Return a file location to a file inside the trajectory folder

        Parameters
        ----------
        f : str or `OutputTypeDescription`
            the filename to be appended to the trajectories directory

        Returns
        -------
        `File`
            the object containing the location

        """
        if isinstance(f, six.string_types):
            return File(os.path.join(self.location, f))
        elif isinstance(f, OutputTypeDescription):
            return self.file(f.filename)

    def run(self, resource_name=None, export_path=None,
            cpu_threads=1, gpu_contexts=0, mpi_rank=0):
        """
        Return a task to run the engine for this trajectory

        This method is used to link the `Trajectory` object
        to an MD Program's AdaptiveMD Engine

        Returns
        -------
        `Task`
            the task object that can be submitted to the queue

        """
        # TODO check that you can generate one trajectory object only once
        # not just the task for it

        if self.engine:
            return self.engine.run(self, resource_name, export_path,
                                   cpu_threads, gpu_contexts, mpi_rank)
        else:
            return None

    def extend(self, length, export_path=None, gpu_contexts=0,
               resource_name=None, cpu_threads=1, mpi_rank=0):
        """
        Get a task to extend this trajectory if the engine is set

        Parameters
        ----------
        length : int or list of int
            the length to extend by as a single int or a list of ints

        Returns
        -------
        `Task`
            the task object to extend the trajectory

        """
        if self.engine:
            if isinstance(length, int):
                length = [length]

            # make sure we have a list now
            assert(isinstance(length, (tuple, list)))

            x = self
            for l in length:
                x = x.engine.extend(x, l, export_path=export_path, gpu_contexts=gpu_contexts,
                     resource_name=resource_name, cpu_threads=cpu_threads, mpi_rank=mpi_rank)

            return x
        else:
            return None

    def outputs(self, outtype):
        """
        Get a location to the file containing the output by given name

        Parameters
        ----------
        outtype : str or `OutputTypeDescription`
            the name of the outputtype as str or the full description object

        Returns
        -------
        `File`
            a file location that points to the concrete file that contains
            the data for a particular output type

        """
        if self.engine:
            if isinstance(outtype, six.string_types):
                if outtype in self.engine.types:
                    return self.file(self.engine.types[outtype])
            elif isinstance(outtype, OutputTypeDescription):
                return self.file(outtype)

        return None

    @property
    def types(self):
        """
        Return the OutputTypeDescriptions for this trajectory

        Returns
        -------
        dict str: `OutputTypeDescription`
            the output description dict of the engine

        """
        if self.engine:
            return self.engine.types

        return None

    @property
    def existing_frames(self):
        """
        Returns
        -------
        list of int
            a sorted list of frame indices with full coordinates that can be
            used for restart. relative to the engines timesteps

        """
        full_strides = self.engine.full_strides
        frames = set()
        l = len(self) + 1
        for stride in full_strides:
            frames.update(range(0, l, stride))

        return sorted(frames)


class Frame(StorableMixin):
    """
    Represents a frame of a trajectory

    Attributes
    ----------
    trajectory : `Trajectory`
        the origin trajectory
    index : int
        the frame index staring from zero

    """
    def __init__(self, trajectory, index):
        super(Frame, self).__init__()
        self.trajectory = trajectory
        self.index = index

    def __repr__(self):
        return 'Frame(%s[%d])' % (self.trajectory.short, self.index)

    @property
    def index_in_outputs(self):
        """
        Return output type and effective frame index for this frame

        Returns
        -------
        str
            the name of the output type
        int
            the effective index within this trajectory obeying the trajectories
            own stride

        """
        absolute_idx = self.index

        if absolute_idx > self.trajectory.length:
            return None, None

        if self.trajectory.types:
            for key, desc in self.trajectory.types.items():
                stride = desc.stride
                if desc.selection is None:
                    # full atoms
                    if absolute_idx % stride == 0:
                        # picked a frame that exists in this stride
                        return key, absolute_idx // stride

        return None, None

    @property
    def exists(self):
        """
        Returns
        -------
        bool
            if True there is a concrete trajectory file with full
            coordinates for this frame

        """
        ty, idx = self.index_in_outputs
        return ty is not None


class TrajectoryGenerationTask(PrePostTask):
    """
    A task that will generate a trajectory

    """

    _copy_attributes = PrePostTask._copy_attributes + [
            'trajectory'
        ]

    def _default_success(self, scheduler, path=None):
        super(TrajectoryGenerationTask, self)._default_success(scheduler, path)

        # # give the used engine the credit for making the trajectory
        # for t in self.targets:
        #     if isinstance(t, Trajectory):
        #         t.engine = self.generator

    def __init__(self, generator=None, trajectory=None, resource_name=None,
                 est_exec_time=5, cpu_threads=1, gpu_contexts=0, mpi_rank=0):

        super(TrajectoryGenerationTask, self).__init__(
            generator, resource_name=resource_name, est_exec_time=est_exec_time,
            cpu_threads=cpu_threads, gpu_contexts=gpu_contexts, mpi_rank=mpi_rank)

        # set this engine to be run by this
        self.trajectory = trajectory
        if trajectory:
            trajectory.engine = self.generator

    def extend(self, length, export_path=None):
        """
        Extend the trajectory that was generated by this task

        Parameters
        ----------
        length : int
            the number of frames resp to native engine timesteps

        Returns
        -------
        `Task`
            a task to extend the current trajectory

        """
        t = self.generator.extend(self.trajectory, length, export_path=export_path)

        # this is not really necessary since we require internally that the
        # source exists but this will cause all dependencies to be
        # submitted, too
        t.dependencies = [self]
        return t


class TrajectoryExtensionTask(TrajectoryGenerationTask):
    """
    A task that generates a trajectory out of a source trajectory

    """

    _copy_attributes = TrajectoryGenerationTask._copy_attributes + [
            'source'
        ]

    def __init__(self, generator=None, trajectory=None, source=None, resource_name=None,
                 est_exec_time=5, cpu_threads=1, gpu_contexts=0, mpi_rank=0):

        super(TrajectoryExtensionTask, self).__init__(
            generator, trajectory, resource_name=resource_name, est_exec_time=est_exec_time,
            cpu_threads=cpu_threads, gpu_contexts=gpu_contexts, mpi_rank=mpi_rank)

        self.source = source

    @property
    def ready(self):
        # an extension is ready to be executed, if the source also exists!
        if not self.source.exists:
            return False

        # and dependencies need to be done
        if not self.dependency_okay:
            return False

        return True


class OutputTypeDescription(StorableMixin):
    """
    A description of a general trajectory type

    Attributes
    ----------
    filename : str
        a filename to store these type of trajectory in
    stride : int
        the stride to be used relative to native engine timesteps
    selection : str
        a :meth:`mdtraj.Topolopgy.select` like selection of an atom subset

    """
    def __init__(self, filename=None, stride=1, selection=None):
        super(OutputTypeDescription, self).__init__()

        if filename is None:
            filename = 'stride-%d.dcd' % stride

        self.filename = filename
        self.stride = stride
        self.selection = selection
