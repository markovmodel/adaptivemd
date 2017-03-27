from adaptivemd.generator import PythonRPCTaskGenerator
from adaptivemd.task import PythonTask

import shutil
import os


class Archiver(PythonRPCTaskGenerator):
    """
    An generator that will essentially copy all files in a project to a specified location

    Attributes
    ----------
    target : `Directory`
        the directory to dump all simulations to

    """

    def __init__(self, target):
        super(Archiver, self).__init__()
        self.target = target

    def to_dict(self):
        return {
            'target': self.target
        }

    def task_archive(self, files):
        """
        Create a task that computes an msm using a given set of trajectories

        Parameters
        ----------
        files : list of `Trajectory`
            the list of trajectory references to be used in the computation

        Returns
        -------
        `Task`
            a task object describing a simple python RPC call using pyemma

        """

        t = PythonTask()

        t.link(self.target, 'target_folder')
        t.call(copy_files, files=files)

        return t


def copy_files(files):
    names = {}
    for f in files:
        n = os.path.basename(f)
        if n not in names:
            shutil.copy(f, os.path.join('target_folder', n))
            names[n] = 1
        else:
            parts = n.split('.')
            n2 = '.'.join(parts[:-1]) + '-{count:08d}.'.format(count=names[n]) + parts[-1]
            shutil.copy(f, os.path.join('target_folder', n2))
            names[n] += 1
