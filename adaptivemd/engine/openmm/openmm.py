import os

from adaptivemd.task import PythonTask
from adaptivemd.file import Location, File
from adaptivemd.engine import Engine, Frame, Trajectory, \
    TrajectoryGenerationTask, TrajectoryExtensionTask


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

    def __init__(self, system_file, integrator_file, pdb_file, args=None, restartable=True):
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
            args = '-p CPU --store-interval 1'

        self.args = args
        self.restartable = restartable

    @property
    def call_format_str(self):
        return 'python openmmrun.py %s {3} -t {0} --length {1} {2}' % self.args

    @staticmethod
    def then_func_import(project, task, data, inputs):
        for f in data:
            # check if file with same location exists
            if f not in project.files:
                project.files.update(f)

    def task_run_trajectory(self, target):
        t = TrajectoryGenerationTask(self, target)

        initial_pdb = t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.link(self['system_file_stage'])
        t.link(self['integrator_file_stage'])
        t.link(self['_executable_file_stage'])

        if target.frame in [self['pdb_file'], self['pdb_file_stage']]:
            input_pdb = initial_pdb

        elif isinstance(target.frame, File):
            loc = Location('coordinates.%s' % target.frame.extension)
            input_pdb = t.get(target.frame, loc)

        elif isinstance(target.frame, Frame):
            input_traj = t.link(target.frame.trajectory.file('output.dcd'))
            input_pdb = File('input.pdb')

            t.append('mdconvert -o %s -i %d -t %s %s' % (
                input_pdb, target.frame.index, initial_pdb, input_traj))
        else:
            # for now we assume that if the initial frame is None or
            # not specific use the engines internal. That should be changed
            # todo: Raise exception here

            return

        # this represents our output trajectory
        output = Trajectory('traj/', target.frame, length=target.length, engine=self)

        # create the directory
        t.touch(output)

        cmd = 'python openmmrun.py {args} -t {pdb} --length {length} {output}'.format(
            pdb=input_pdb,
            length=target.length,
            output=output,
            args=self.args,
        )
        t.append(cmd)

        t.put(output, target)

        return t

    def task_extend_trajectory(self, source, length):
        if length < 0:
            return []

        # create a new file, but with the same name, etc, just new length
        target = source.clone()
        target.length = len(source) + length

        t = TrajectoryExtensionTask(self, target, source)

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

        cmd = ('python openmmrun.py {args} --restart {restart} -t {pdb} '
               '--length {length} {output}').format(
            pdb=initial_pdb,
            restart=source.file('restart.npz'),  # todo: this is engine specific!
            length=target.length - source.length,
            output=extension,
            args=self.args
        )
        t.append(cmd)

        # join both trajectories
        t.append('mdconvert -o {output} -t {pdb} {source} {extension}'.format(
            output=extension.file('extension.dcd'),
            pdb=initial_pdb,
            source=source_link.file('output.dcd'),
            extension=extension.file('output.dcd')
        ))

        # rename joined extended.dcd into output.dcd
        t.append(extension.file('extension.dcd').move(extension.file('output.dcd')))

        # now extension/ should contain all files as expected
        # move extended trajectory to target place (replace old) files
        # this will also register the new trajectory folder as existent
        t.put(extension, target)

        return t

    def task_import_trajectory_folder(self, source):
        t = PythonTask(self)

        t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.call(scan_trajectories, source)

        # call `then_func_import` after success
        t.then('then_func_import')

        return t


def scan_trajectories(source):
    import glob
    import mdtraj as md

    files = glob.glob(source)

    here = os.getcwd()

    reference_list = []
    for f in files:

        rel = os.path.relpath(f, here)

        if rel.startswith('../../../../'):
            p = 'worker://' + os.path.abspath(f)
        elif rel.startswith('../../../'):
            p = 'shared://' + rel[8:]
        elif rel.startswith('../../'):
            p = 'sandbox://' + rel[5:]
        else:
            p = 'worker://' + os.path.abspath(f)

        # print f, rel, p

        traj = md.load(f, top='initial.pdb')
        reference = Trajectory(p, None, len(traj))
        reference_list.append(reference)

    return reference_list
