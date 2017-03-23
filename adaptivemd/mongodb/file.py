import logging
from uuid import UUID

from object import ObjectStore

logger = logging.getLogger(__name__)


class FileStore(ObjectStore):

    def __init__(self, name, content_class):
        super(FileStore, self).__init__(name, content_class)

        # Something todo ?
        # claim GridFS

        self.grid = None

    def consume_one(self, test_fnc=None):
        raise NotImplementedError()

    def modify_one(self, key, value, update):
        raise NotImplementedError()

    def modify_test_one(self, test_fnc, key, value, update):
        raise NotImplementedError()

    def load_indices(self):
        self.index = [int(UUID(x)) for x in self.grid.list()]

    def __len__(self):
        if hasattr(self, '_document'):
            if self._document:
                return self._document.count()

        return 0

    def _load(self, idx):
        # LOAD FROM GridFS
        name = str(UUID(int=idx))
        f = self.grid.find_one({'filename': name})
        obj = self.storage.simplifier.from_json(f.read())
        obj.__store__ = self
        return obj

    def cache_all(self):
        pass

    def _save(self, obj):
        # LOAD FROM GridFS
        name = str(UUID(int=obj.__uuid__))
        s = self.storage.simplifier.to_json(obj)
        self.grid.put(s, filename=name)
        obj.__store__ = self
        return obj

    # ==========================================================================
    # LOAD/SAVE DECORATORS FOR CACHE HANDLING
    # ==========================================================================

    def find_one(self, dct):
        raise NotImplementedError()