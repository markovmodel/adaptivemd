from file import File
from mongodb import StorableMixin
import os


class TaskGenerator(StorableMixin):
    """
    A generator for `Task` objects
    """
    def __init__(self):
        super(TaskGenerator, self).__init__()
        self._items = dict()
        self.initial_staging = []

    def __getitem__(self, item):
        return self._items[item]

    def __setitem__(self, key, value):
        self._items[key] = value

    def items(self):
        return self._items.items()

    @classmethod
    def from_dict(cls, dct):
        obj = cls.__new__(cls)
        StorableMixin.__init__(obj)
        obj._items = dct['_items']
        obj.initial_staging = dct['initial_staging']
        return obj

    def to_dict(self):
        return {
            '_items': self._items,
            'initial_staging': self.initial_staging
        }

    @property
    def files(self):
        return {
            key: value
            for key, value in self.items() if isinstance(value, File)}

    @property
    def stage_in(self):
        """
        Return a list of actions needed before tasks can be generated

        Returns
        -------
        list of `Action`
            the list of Actions to be parsed into stage in steps

        """
        return self.initial_staging

    def file_generators(self):
        return {}

    def stage(self, obj, target=None):
        self.initial_staging.append(
            obj.transfer(target)
        )

rpc_exec = File('file://' + os.path.join(os.path.dirname(__file__), 'scripts/_run_.py')).load()


class PythonRPCTaskGenerator(TaskGenerator):
    """
    A python remote procedure call that executes a python function remotely
    """
    def __init__(self):
        super(PythonRPCTaskGenerator, self).__init__()

        stage = rpc_exec.transfer('staging:///')
        self.initial_staging.append(stage)
