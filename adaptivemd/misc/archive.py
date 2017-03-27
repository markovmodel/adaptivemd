##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: Jan-Hendrik Prinz
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


from adaptivemd.generator import PythonRPCTaskGenerator
from adaptivemd.task import PythonTask

import shutil
import os


class Archiver(PythonRPCTaskGenerator):
    def __init__(self, target):
        """
        Generator to copy all files in a project to a specified location

        Parameters
        ----------
        target : `Directory`
            the directory to dump all simulations to

        """
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
