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

    def run(self, target):
        return None
