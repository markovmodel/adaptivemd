# Create compute units for various simulation tools
import random
import os

from adaptivemd.file import File
from adaptivemd.generator import TaskGenerator
from adaptivemd.mongodb import StorableMixin, ObjectSyncVariable
from adaptivemd.task import Task


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

    def file_generators(self):
        """
        Return a list of function to be run with certain classes

        `Trajectory` is a natural object of engine and giving a trajectory including its
        initial frame and length is enough to tell the `Engine` on what to generate. Since
        this is enough we can define that using a `Trajectory` object in `Scheduler.submit`
        will result in a simulation task.

        Returns
        -------
        dict of `type`: function
            the dict describing with function to run with which object type

        """
        return {
            Trajectory: self.run
        }

    def add_output_type(self, name, filename=None, stride=1, selection=None):
        self.types[name] = OutputTypeDescription(filename, stride, selection)

    @property
    def native_stride(self):
        return lcmm(*[x.stride for x in self.types.values()])


def gcd(a, b):
    """Return greatest common divisor using Euclid's Algorithm."""
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """Return lowest common multiple."""
    return a * b // gcd(a, b)


def lcmm(*args):
    """Return lcm of args."""
    return reduce(lcm, args)


# ------------------------------------------------------------------------------
# FILE TYPES
# ------------------------------------------------------------------------------

class Trajectory(File):
    """
    Represents a trajectory `File` on the cluster

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
        if 0 <= item < len(self):
            return Frame(self, item)
        else:
            return None

    def __repr__(self):
        return "Trajectory(%r >> %s[0..%d])" % (
            self.frame, self.basename, self.length)

    def pick(self):
        return self[random.randint(0, len(self) - 1)]

    @property
    def is_folder(self):
        # we treat trajectories from now on as Directories
        return True

    def file(self, f):
        if isinstance(f, basestring):
            return File(os.path.join(self.location, f))
        elif isinstance(f, OutputTypeDescription):
            return self.file(f.filename)

    @property
    def restartable(self):
        return True

    def run(self):
        if self.engine:
            return self.engine.run(self)
        else:
            return None

    def extend(self, length):
        """
        Get a task to extend this trajectory if the engine is set

        Parameters
        ----------
        length : int
            the length to extend by

        Returns
        -------
        `Task`
            the task object
        """
        if self.engine:
            return self.engine.extend(self, length)
        else:
            return None

    def outputs(self, outtype):
        """
        Get a location to the file containing the output by given name

        Parameters
        ----------
        outtype : str ot `OutputTypeDescription`

        Returns
        -------
        `File`
            a file location that points to the concrete file that contains
            the data for a particular output type

        """
        if self.engine:
            if isinstance(outtype, basestring):
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

    @property
    def location(self):
        return self.trajectory.location

    def __repr__(self):
        return 'Frame(%s[%d])' % (self.trajectory.basename, self.index)

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

        if self.trajectory.types:
            for key, desc in self.trajectory.types.iteritems():
                stride = desc.stride
                if desc.selection is None:
                    # full atoms
                    if absolute_idx % stride == 0:
                        # picked a frame that exists in this stride
                        return key, absolute_idx / stride

        return None, None

    @property
    def exists(self):
        ty, idx = self.index_in_outputs
        return ty is not None

# class RestartFile(File):
#     """
#     Represents a restart (velocities) `File` on the cluster
#
#     """
#
#     def __repr__(self):
#         return "RestartFile(%s)" % (
#             self.basename)


class TrajectoryGenerationTask(Task):
    """
    A task that will generate a trajectory
    """

    _copy_attributes = Task._copy_attributes + [
            'trajectory'
        ]

    def _default_success(self, scheduler):
        super(TrajectoryGenerationTask, self)._default_success(scheduler)

        # # give the used engine the credit for making the trajectory
        # for t in self.targets:
        #     if isinstance(t, Trajectory):
        #         t.engine = self.generator

    def __init__(self, generator=None, trajectory=None):
        super(TrajectoryGenerationTask, self).__init__(generator)

        # set this engine to be run by this
        self.trajectory = trajectory
        if trajectory:
            trajectory.engine = self.generator

    def extend(self, length):
        t = self.generator.extend(self.trajectory, length)

        # this is not really necessary since we require internally that the source exists
        # but this will cause all dependencies to be submitted, too
        t.dependencies = [self]
        return t


class TrajectoryExtensionTask(TrajectoryGenerationTask):
    """
    A task that generates a trajectory out of a source trajectory
    """

    _copy_attributes = TrajectoryGenerationTask._copy_attributes + [
            'source'
        ]

    def __init__(self, generator=None, trajectory=None, source=None):
        super(TrajectoryExtensionTask, self).__init__(generator, trajectory)
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
    def __init__(self, filename=None, stride=1, selection=None):
        super(OutputTypeDescription, self).__init__()

        if filename is None:
            filename = 'stride-%d.dcd' % stride

        self.filename = filename
        self.stride = stride
        self.selection = selection
