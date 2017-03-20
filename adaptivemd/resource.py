from mongodb import StorableMixin
from task import DummyTask


class Resource(StorableMixin):
    """
    Representation of a shared FS with attached cluster(s)

    Similar to a resource in RP
    """

    def __init__(self, shared_path=None, wrapper=None):
        super(Resource, self).__init__()
        if shared_path is None:
            shared_path = '$HOME/adaptivemd/'

        self.shared_path = shared_path
        if wrapper is None:
            wrapper = DummyTask()

        self.wrapper = wrapper


class AllegroCluster(Resource):
    """
    The FUB Allegro cluster and its queues
    """
    def __init__(self, shared_path=None):
        if shared_path is None:
            shared_path = '$HOME/NO_BACKUP/adaptivemd/'

        super(AllegroCluster, self).__init__(shared_path=shared_path)

    def add_cuda_module(self):
        """
        Add loading the CUDA module

        """
        w = self.wrapper
        w.pre.append(
            'export MODULEPATH=/import/ag_cmb/software/modules:$MODULEPATH')
        w.pre.append('module load cuda/7.5')


class LocalCluster(Resource):
    pass
