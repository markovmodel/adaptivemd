# Create compute units for various simulation tools
import random
import os

from adaptivemd.file import File, Location
from adaptivemd.generator import TaskGenerator
from adaptivemd.mongodb import StorableMixin, SyncVariable
from adaptivemd.task import Task


class Engine(TaskGenerator):
    """
    An generator for trajectory simulation tasks

    """

    def task_run_trajectory(self, target):
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
            Trajectory: self.task_run_trajectory
        }


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

    engine = SyncVariable('engine', lambda x: not bool(x))

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
        return File(os.path.join(self.location, f))

    @property
    def restartable(self):
        return True


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

    def __init__(self, generator=None, trajectory=None):
        super(TrajectoryGenerationTask, self).__init__(generator)
        self.trajectory = trajectory

    def extend(self, length):
        t = self.generator.task_extend_trajectory(self.trajectory, length)

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
