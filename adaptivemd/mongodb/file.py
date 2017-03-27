import logging
import gridfs
from uuid import UUID

from base import StorableMixin
from object import ObjectStore
from proxy import LoaderProxy

logger = logging.getLogger(__name__)


class FileStore(ObjectStore):

    def __init__(self, name, content_class):
        super(FileStore, self).__init__(name, content_class)
        self.grid = None

    def initialize(self):
        self.grid = gridfs.GridFS(self.storage.db)
        self._created = True

    def restore(self):
        self.grid = gridfs.GridFS(self.storage.db)

    def consume_one(self, test_fnc=None):
        raise NotImplementedError()

    def modify_one(self, key, value, update):
        raise NotImplementedError()

    def modify_test_one(self, test_fnc, key, value, update):
        raise NotImplementedError()

    def load_indices(self):
        self.index = [long(x, 16) for x in self.grid.list()]

    def __len__(self):
        if self.grid:
            return len(list(self.grid.find()))

        return 0

    def _load(self, idx):
        _id = hex(idx)
        f = self.grid.find_one({'_id': _id})
        obj = self.storage.simplifier.from_json(f.read())
        obj.__store__ = self
        obj.__uuid__ = idx
        obj.__time__ = f._time  # use time or 0 if unset

        return obj

    def cache_all(self):
        pass

    def _save(self, obj):
        _id = hex(obj.__uuid__)

        s = self.storage.simplifier.to_json_object(obj)
        if hasattr(obj, 'name'):
            self.grid.put(
                s,
                filename=obj.name,
                _id=_id,
                _time=obj.__time__
                **{x: getattr(obj, x) for x in self._find_by})  # add search indices
        else:
            self.grid.put(
                s,
                _id=_id,
                _time=obj.__time__,
                **{x: getattr(obj, x) for x in self._find_by})  # add search indices

        obj.__store__ = self
        return obj

    # ==========================================================================
    # LOAD/SAVE DECORATORS FOR CACHE HANDLING
    # ==========================================================================

    def find_one(self, dct):
        idx = self.grid.find_one(dct)['filename']
        return self.load(int(UUID(idx)))

    def load(self, idx):
        """
        Returns an object from the storage.

        Parameters
        ----------
        idx : int
            the integer index of the object to be loaded

        Returns
        -------
        :py:class:`mongodb.base.StorableMixin`
            the loaded object
        """

        if type(idx) is str:
            idx = long(UUID(self.grid.find_one({'filename': idx})['_id']), 16)

        if type(idx) is long:
            pass

        elif type(idx):
            raise ValueError((
                'indices of type "%s" are not allowed in named storage '
                '(only str and long)') % type(idx).__name__
            )

        # if it is in the cache, return it
        try:
            obj = self.cache[idx]
            logger.debug('Found IDX #' + str(idx) + ' in cache. Not loading!')
            if idx not in self.index:
                # update cache
                self.index.append(idx)

            return obj

        except KeyError:
            pass

        logger.debug(
            'Calling load object of type `%s` @ IDX #%d' %
            (self.content_class.__name__, idx))

        obj = self._load(idx)

        logger.debug(
            'Calling load object of type %s and IDX # %d ... DONE' %
            (self.content_class.__name__, idx))

        if obj is not None:
            # update cache there might have been a change due to naming
            self.cache[idx] = obj

            if idx not in self.index:
                # update cache
                self.index.append(idx)

            logger.debug(
                'Try loading UUID object of type %s and IDX # %d ... DONE' %
                (self.content_class.__name__, idx))

        logger.debug(
            'Finished load object of type %s and IDX # %d ... DONE' %
            (self.content_class.__name__, idx))

        return obj

    def save(self, obj):
        """
        Saves an object to the storage.

        Parameters
        ----------
        obj : :class:`mongodb.base.StorableMixin`
            the object to be stored

        """
        uuid = obj.__uuid__

        if uuid in self.index:
            # has been saved so quit and do nothing
            return self.reference(obj)

        # mark as saved so circular dependencies will not cause infinite loops
        n_idx = len(self.index)
        self.index.append(uuid)

        q = self.grid.find_one({'_id': hex(uuid)})

        if q is not None:
            # exists
            return self.reference(obj)

        if isinstance(obj, LoaderProxy):
            if obj._store is self:
                # is a proxy of a saved object so do nothing
                return uuid
            else:
                # it is stored but not in this store so we try storing the
                # full attribute which might be still in cache or memory
                # if that is not the case it will be stored again. This can
                # happen when you load from one store save to another. And load
                # again after some time while the cache has been changed and try
                # to save again the loaded object. We will not explicitly store
                # a table that matches objects between different storages.
                return self.save(obj.__subject__)

        if not isinstance(obj, self.content_class):
            raise ValueError((
                'This store can only store object of base type "%s". Given '
                'obj is of type "%s". You might need to use another store.')
                % (self.content_class, obj.__class__.__name__)
            )

        logger.debug('Saving ' + str(type(obj)) + ' using IDX #' + str(uuid))

        try:
            self._save(obj)
            self.cache[uuid] = obj

        except:
            # in case we did not succeed remove the mark as being saved
            del self.index[n_idx]
            raise

        return self.reference(obj)

    def __contains__(self, item):
        uuid = item.__uuid__

        if item.__uuid__ in self.index:
            return True

        q = self.grid.find_one({'_id': hex(uuid)})

        if q is not None:
            # exists
            self.index.append(uuid)
            return True

        return False


class DataDict(StorableMixin):
    """
    Delegate to the contained .data object
    """
    def __init__(self, data):
        super(DataDict, self).__init__()
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __contains__(self, item):
        return item in self.data

    def __getattr__(self, item):
        return getattr(self.data, item)
