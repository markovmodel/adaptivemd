from adaptivemd.task import Task
from adaptivemd.file import Location, File
from adaptivemd.engine import Engine, Frame, Trajectory


class ACEMDEngine(Engine):
    """
    Implementation of the AceMD engine

    Attributes
    ----------
    conf_file : `File`
        reference to the .conf file
    pdb_file : `File`
        reference to a .pdb file
    args : str
        arguments passed to the AceMD command line

    """

    def __init__(self, conf_file, pdb_file, args=None):
        super(ACEMDEngine, self).__init__()

        self._items = dict()

        self['pdb_file'] = pdb_file
        self['conf_file'] = conf_file

        for name, f in self.files.items():
            stage = f.transfer(Location('staging:///'))
            self[name + '_stage'] = stage.target
            self.initial_staging.append(stage)

        if args is None:
            args = ''

        self.args = args

    @property
    def call_format_str(self):
        return 'acemd %s {0}' % self.args

    def task_run_trajectory(self, target):
        t = Task()

        initial_pdb = t.link(self['pdb_file_stage'], Location('initial.pdb'))
        t.get(self['conf_file_stage'])

        if target in [self['pdb_file'], self['pdb_file_stage']]:
            input_pdb = initial_pdb

        elif isinstance(target.frame, File):
            input_pdb = t.get(target.frame, Location('input.pdb'))

        elif isinstance(target.frame, Frame):
            input_traj = t.link(target.frame.trajectory, Location('input.xtc'))
            input_pdb = File('input.pdb')

            t.append('mdconvert -o %s -i %d -t %s %s' % (
                input_pdb, target.frame.index, initial_pdb, input_traj))
        else:
            # todo: Raise execption here
            return

        t.append('echo "structure %s\nrun %f" >> %s' % (
            input_pdb, target.length, self['conf_file_stage']))

        output_traj = Trajectory(
            'output.xtc', target.frame, length=target.length)

        t.call(
            self.call_format_str,
            input_pdb, target.length, output_traj)

        t.put(output_traj, target)

        return t
