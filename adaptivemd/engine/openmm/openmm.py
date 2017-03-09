import os

from adaptivemd.task import Task, PythonTask
from adaptivemd.file import Location, File
from adaptivemd.engine import Engine, Frame, Trajectory, \
    TrajectoryGenerationTask, RestartFile, TrajectoryExtensionTask


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
    trajectory_ext = 'dcd'

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
            args = '-p CPU --store-interval 1'

        self.args = args

    @property
    def call_format_str(self):
        return 'python openmmrun.py %s {3} -t {0} --length {1} {2}' % self.args

    @staticmethod
    def then_func_import(project, data, inputs):
        for f in data:
            # check if file with same location exists
            if f not in project.files:
                project.files.update(f)

    def _make_single_traj_cmd(self, t, target, initial_pdb, idx='', args=''):
        if target.frame in [self['pdb_file'], self['pdb_file_stage']]:
            input_pdb = initial_pdb

        elif isinstance(target.frame, File):
            loc = Location('coordinates%s.%s' % (idx, target.frame.extension))
            input_pdb = t.get(target.frame, loc)

        elif isinstance(target.frame, Frame):
            input_traj = t.link(target.frame.trajectory, Location('input%s.dcd' % idx))
            input_pdb = File('input%s.pdb' % idx)

            t.pre_bash('mdconvert -o %s -i %d -t %s %s' % (
                input_pdb, target.frame.index, initial_pdb, input_traj))
        else:
            # for now we assume that if the initial frame is None or
            # not specific use the engines internal. That should be changed
            # todo: Raise exception here

            return

        restart_file = File( 'output%s.dcd.restart' % idx)

        output_traj = Trajectory(
            'output%s.dcd' % idx, target.frame, length=target.length)

        cmd = self.call_format_str.format(
            input_pdb,
            target.length,
            output_traj.path,
            args
        )
        t.pre_bash(cmd)

        return output_traj, restart_file

    def _extend_single_traj_cmd(self, t, source, target, initial_pdb, idx='', args=''):

        if source.restart:
            input_pdb = initial_pdb
            loc = Location('in%s.restart' % idx)
            in_restart_file = t.link(source.restart, loc)
            args = ('--restart %s ' % in_restart_file.basename) + args
        else:
            restart_file = None
            input_traj = t.link(source, Location('input%s.dcd' % idx))
            input_pdb = File('input%s.pdb' % idx)

            t.pre_bash('mdconvert -o %s -i %d -t %s %s' % (
                input_pdb, -1, initial_pdb, input_traj))

        restart_file = RestartFile('extension%s.dcd.restart' % idx)
        output_traj = Trajectory(
            'extension%s.dcd' % idx, source.frame, length=target.length)

        cmd = self.call_format_str.format(
            input_pdb,
            target.length - source.length,
            output_traj.path,
            args
        )
        t.pre_bash(cmd)

        return output_traj, restart_file

    def task_run_trajectory(self, target):
        t = TrajectoryGenerationTask(self, target)

        initial_pdb = t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.link(self['system_file_stage'])
        t.link(self['integrator_file_stage'])
        t.link(self['_executable_file_stage'])

        t.pre_bash('hostname')

        output_traj, restart_file = \
            self._make_single_traj_cmd(t, target, initial_pdb)

        t.call('echo "DONE!"')

        if target.restart:
            t.put(restart_file, target.restart)

        t.put(output_traj, target)

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

        source_traj = t.link(source, Location('source%s.dcd' % ''))

        extension_traj, restart_file = \
            self._extend_single_traj_cmd(t, source, target, initial_pdb)

        output_traj = Trajectory(
            'output%s.dcd' % '', target.frame, length=target.length)

        # join both trajectories
        t.pre_bash('mdconvert -o %s -t %s %s %s' % (
            output_traj, initial_pdb, source_traj, extension_traj))

        t.call('echo {0}', 'DONE!')

        if target.restart:
            t.put(restart_file, target.restart)

        t.put(output_traj, target)

        return t

    def task_import_trajectory_folder(self, source):
        t = PythonTask(self)

        t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.call(scan_trajectories, source)

        # call `then_func_import` after success
        t.then('then_func_import')

        return t


exec_file = File('file://' + os.path.join(os.path.dirname(__file__), 'openmmrun.py')).load()


class OpenMMEngine4CUDA(OpenMMEngine):
    """
    OpenMM Engine to be used by Adaptive MD that runs 4 trajectories in parallel

    Attributes
    ----------
    system_file : `File`
        the system.xml file for OpenMM
    integrator_file : `File`
        the integrator.xml file for OpenMM
    pdb_file : `File`
        the .pdb file for the topology
    args : str
        a list of arguments passed to the openmmrun.py script
    """
    trajectory_ext = 'dcd'

    def __init__(self, system_file, integrator_file, pdb_file, device_indices=None, args=None):
        if args is None:
            args = '--store-interval 1'

        if device_indices is None:
            device_indices = range(4)

        device_indices = map(str, device_indices)
        super(OpenMMEngine4CUDA, self).__init__(system_file, integrator_file, pdb_file, args)

        self.device_indices = device_indices

    @property
    def call_format_str(self):
        return 'python openmmrun.py %s {3} -t {0} --length {1} {2} &' % self.args

    def task_run_trajectory(self, targets):
        t = Task(self)

        initial_pdb = t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.link(self['system_file_stage'])
        t.link(self['integrator_file_stage'])
        t.link(self['_executable_file_stage'])

        outs = [
            self._make_single_traj_cmd(
                t, target, initial_pdb, str(idx),
                '--cuda-device==' + str(self.device_indices[idx]))
            for idx, target in enumerate(targets)]

        # wait until all are finished
        t.pre_bash('wait')
        t.call('echo "DONE!"')

        for out, target in zip(outs, targets):
            if target.restart:
                t.put(out[1], target.restart)

            t.put(out[0], target)

        return t

    # todo: fix this!
    def task_restart_trajectory(self, sources, lengths):
        if isinstance(lengths, int):
            lengths = [lengths] * len(sources)

        for source, length in zip(sources, lengths):
            if not source.restart or length <= source.length:
                # either we already have a long trajectory or there is no restart file
                return []

        t = Task(self)

        initial_pdb = t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.link(self['system_file_stage'])
        t.link(self['integrator_file_stage'])
        t.link(self['_executable_file_stage'])

        targets = []
        outs = []

        for idx, (source, length) in enumerate(zip(sources, lengths)):
            # link the source and its restart file
            t.link(source, 'source%s.dcd' % str(idx))
            restart_file = t.link(source.restart, 'restart%s.restart' % str(idx))

            target = source.clone()
            target.length = length
            targets.append(target)

            outs.append(self._make_single_traj_cmd(t, restart_file, initial_pdb))

        t.call('echo "DONE!"')

        for out, target in zip(outs, targets):
            if target.restart:
                t.put(out[1], target.restart)

            t.put(out[0], target)

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

        print f, rel, p

        traj = md.load(f, top='initial.pdb')
        reference = Trajectory(p, None, len(traj))
        reference_list.append(reference)

    return reference_list
