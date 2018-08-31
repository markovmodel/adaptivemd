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
from __future__ import absolute_import

import os
import ujson

# from adaptivemd.task import PythonTask
from adaptivemd.file import Location, File
from adaptivemd.engine import (Engine, Frame, Trajectory,
                               TrajectoryGenerationTask, TrajectoryExtensionTask)


exec_file = File('file://' + os.path.join(os.path.dirname(__file__), 'openmmrun.py')).load()


class OpenMMEngine(Engine):
    """
    OpenMM Engine to be used by Adaptive MD

    Attributes
    ----------
    system_file : `File`
        the system.xml file for OpenMM
    integrator_file : `File`
        the integrator.xml file for OpenMM
    pdb_file : `File`
        the .pdb file for the topology
    args : str
        a list of arguments passed to the `openmmrun.py` script
    """

    def __init__(self, system_file, integrator_file, pdb_file, args=None):
        super(OpenMMEngine, self).__init__()

        self._items = dict()

        self['pdb_file'] = pdb_file
        self['system_file'] = system_file
        self['integrator_file'] = integrator_file
        self['_executable_file'] = exec_file

        for name, f in self.files.items():
            stage = f.transfer(Location('staging:///'))
            self[name + '_stage'] = stage.target
            self.initial_staging.append(stage)

        if args is None:
            args = '-p CPU'

        self.args = args

    @classmethod
    def from_dict(cls, dct):
        obj = super(OpenMMEngine, cls).from_dict(dct)
        obj.args = dct['args']
        return obj

    def to_dict(self):
        dct = super(OpenMMEngine, self).to_dict()
        dct.update({
            'args': self.args})
        return dct

    @staticmethod
    def then_func_import(project, task, data, inputs):
        for f in data:
            # check if file with same location exists
            if f not in project.files:
                project.files.update(f)

    def _create_output_str(self):
        d = dict()
        for name, opt in self.types.items():
            d[name] = opt.to_dict()

        return '--types="%s"' % ujson.dumps(d).replace('"', "'")

    def run(self, target, resource_name=None, export_path=None,
            cpu_threads=1, gpu_contexts=0, mpi_rank=0):

        t = TrajectoryGenerationTask(self, target, cpu_threads=cpu_threads, 
                               gpu_contexts=gpu_contexts, mpi_rank=mpi_rank)

        if resource_name is None:
            resource_name = list()
        elif isinstance(resource_name, str):
            resource_name = [resource_name]

        assert isinstance(resource_name, list)
        t.resource_name = resource_name

        if export_path:
            t.append(export_path)

        initial_pdb = t.pre_link(self['pdb_file_stage'], Location('initial.pdb'))
        t.pre_link(self['system_file_stage'])
        t.pre_link(self['integrator_file_stage'])
        t.pre_link(self['_executable_file_stage'])

        if target.frame in [self['pdb_file'], self['pdb_file_stage']]:
            input_pdb = initial_pdb

        elif isinstance(target.frame, File):
            loc = Location('coordinates.%s' % target.frame.extension)
            input_pdb = t.get(target.frame, loc)

        elif isinstance(target.frame, Frame):
            input_traj = t.pre_link(target.frame.trajectory, 'source/')
            input_pdb = File('input.pdb')

            # frame index is in canonical stride = 1
            # we need to figure out which frame in the traj this actually is
            # also, we need a traj with full coordinates / selection = None

            ty, idx = target.frame.index_in_outputs

            if ty is None:
                # cannot use a trajectory where we do not have full coordinates
                return

            t.pre.append('mdconvert -o {target} -i {index} -t {pdb} {source}'.format(
                target=input_pdb,  # input.pdb is used as starting structure
                index=idx,         # the index from the source trajectory
                pdb=initial_pdb,   # use the main pdb
                source=input_traj.outputs(ty)))  # we pick output ty
        else:
            # for now we assume that if the initial frame is None or
            # not specific use the engines internal. That should be changed
            # todo: Raise exception here

            return

        # this represents our output trajectory
        output = Trajectory('traj/', target.frame, length=target.length, engine=self)

        # create the directory
        t.touch(output)

        # TODO option for retry
        # TODO use filenames from engine
        retry = '\nj=0\ntries=10\nsleep=1\n'
        retry += '\ntrajfile=traj/protein.dcd\n\n'
        retry += 'while [ $j -le $tries ]; do if ! [ -s $trajfile ]; then {0}; fi; sleep 1; j=$((j+1)); done'

        cmd = 'python openmmrun.py {args} {types} -s {system} -i {integrator} -t {pdb} --length {length} {output}'.format(
            pdb=input_pdb,
            types=self._create_output_str(),
            length=target.length,
            system=self['system_file'].basename,
            integrator=self['integrator_file'].basename,
            output=output,
            args=self.args,
        )

        cmd = retry.format(cmd)
        t.append(cmd)

        t.put(output, target)

        return t

    def extend(self, source, length, resource_name=None, export_path=None,
               cpu_threads=1, gpu_contexts=0, mpi_rank=0):

        if length < 0:
            return []

        # create a new file, but with the same name, etc, just new length
        target = source.clone()
        target.length = len(source) + length

        t = TrajectoryExtensionTask(self, target, source, cpu_threads=cpu_threads,
                                    gpu_contexts=gpu_contexts, mpi_rank=mpi_rank,
                                    )#resource_name=resource_name, export_path=export_path)

        if resource_name is None:
            resource_name = list()
        elif isinstance(resource_name, str):
            resource_name = [resource_name]

        assert isinstance(resource_name, list)
        t.resource_name = resource_name

        if export_path:
            t.append(export_path)

        initial_pdb = t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.link(self['system_file_stage'])
        t.link(self['integrator_file_stage'])
        t.link(self['_executable_file_stage'])

        # this represents our output trajectory
        source_link = t.link(source, 'source/')

        extension = Trajectory(
            'extension/',
            target.frame,
            length=target.length,
            engine=self)

        t.touch(extension)

        # TODO option for retry
        # TODO use filenames from engine
        retry = '\nj=0\ntries=10\nsleep=1\n'
        retry += '\ntrajfile=extension/protein.dcd\n\n'
        retry += 'while [ $j -le $tries ]; do if ! [ -s $trajfile ]; then {0}; fi; sleep 1; j=$((j+1)); done'

        cmd = ('python openmmrun.py {args} {types} -s {system} -i {integrator} --restart {restart} -t {pdb} '
               '--length {length} {output}').format(
            pdb=initial_pdb,
            restart=source.file('restart.npz'),  # todo: this is engine specific!
            length=target.length - source.length,
            system=self['system_file'].basename,
            integrator=self['integrator_file'].basename,
            output=extension,
            args=self.args,
            types=self._create_output_str()
        )

        cmd = retry.format(cmd)
        t.append(cmd)

        # join both trajectories for all outputs
        for ty, desc in self.types.items():
            # stride = desc['stride']

            outname = ty + '.temp.dcd'
            t.post.append('mdconvert -o {output} {source} {extension}'.format(
                output=extension.file(outname),
                source=source_link.outputs(ty),
                extension=extension.outputs(ty)
            ))

            # rename joined extended.dcd into output.dcd
            t.post.append(extension.file(outname).move(extension.outputs(ty)))

        # now extension/ should contain all files as expected
        # move extended trajectory to target place (replace old) files
        # this will also register the new trajectory folder as existent
        t.post_put(extension, target)

        return t

#     def task_import_trajectory_folder(self, source):
#         t = PythonTask(self)
#
#         t.link(self['pdb_file_stage'], Location('initial.pdb'))
#         t.call(scan_trajectories, source=source)
#
#         # call `then_func_import` after success
#         t.then('then_func_import')
#
#         return t
#
#
# def scan_trajectories(source):
#     import glob
#     import mdtraj as md
#
#     files = glob.glob(source)
#
#     here = os.getcwd()
#
#     reference_list = []
#     for f in files:
#
#         rel = os.path.relpath(f, here)
#
#         if rel.startswith('../../../../'):
#             p = 'worker://' + os.path.abspath(f)
#         elif rel.startswith('../../../'):
#             p = 'shared://' + rel[8:]
#         elif rel.startswith('../../'):
#             p = 'sandbox://' + rel[5:]
#         else:
#             p = 'worker://' + os.path.abspath(f)
#
#         # print f, rel, p
#
#         traj = md.load(f, top='initial.pdb')
#         reference = Trajectory(p, None, len(traj))
#         reference_list.append(reference)
#
#     return reference_list
