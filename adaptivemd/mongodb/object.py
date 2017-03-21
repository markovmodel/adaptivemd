import logging
from uuid import UUID
from weakref import WeakValueDictionary

from base import StorableMixin
from cache import MaxCache, Cache, NoCache, \
    WeakLRUCache
from proxy import LoaderProxy

logger = logging.getLogger(__name__)


# class HashedList(dict):
#     def __init__(self):
#         super(HashedList, self).__init__()
#         dict.__init__(self)
#         self._list = []
#
#     def append(self, key):
#         dict.__setitem__(self, key, len(self))
#         self._list.append(key)
#
#     # noinspection PyCallByClass
#     def extend(self, t):
#         l = len(self)
#         map(lambda x, y: dict.__setitem__(self, x, y), t, range(l, l + len(t)))
#         self._list.extend(t)
#
#     def __setitem__(self, key, value):
#         dict.__setitem__(self, key, value)
#         self._list[value] = key
#
#     def __getitem__(self, key):
#         return dict.__getitem__(self, key)
#
#     def index(self, key):
#         return self._list[key]
#
#     def mark(self, key):
#         if key not in self:
#             dict.__setitem__(self, key, -2)
#
#     def unmark(self, key):
#         if key in self:
#             dict.__delitem__(self, key)
#
#     def clear(self):
#         dict.clear(self)
#         self._list = []
#
#     @property
#     def list(self):
#         return self._list


class ObjectStore(StorableMixin):
    """
    Base Class for storing complex objects in a netCDF4 file. It holds a
    reference to the store file.`

    Attributes
    ----------
    content_class : :obj:`mongodb.base.StorableMixin`
        a reference to the class type to be stored using this Storage. Must be
        subclassed from :obj:`mongodb.base.StorableMixin`
    cache : :py:class:`mongodb.cache.Cache`
        a dictionary that holds references to all stored elements by index
        or string for named objects. This is only used for cached access
        if caching is not `False`. Must be of type
        :obj:`mongodb.base.StorableMixin` or subclassed.

    """
    _restore_non_initial_attr = False

    allowed_types = [
        'int', 'float', 'long', 'str', 'bool',
        'numpy.float32', 'numpy.float64',
        'numpy.int8', 'numpy.inf16', 'numpy.int32', 'numpy.int64',
        'numpy.uint8', 'numpy.uinf16', 'numpy.uint32', 'numpy.uint64',
        'index', 'length', 'uuid'
    ]

    default_store_chunk_size = 256
    default_cache = 10000

    def __init__(self, name, content_class):
        """

        Parameters
        ----------
        name : str
        content_class : class

        Notes
        -----
        Usually you want caching, but limited. Recommended is to use an LRUCache
        with a reasonable maximum number of objects that depends on the typical
        number of objects to cache and their size

        The class that takes care of storing data in a file is called a
        `Storage`, so the netCDF+ subclassed `Storage` is a storage.
        The classes that know how to load and save an object from the storage
        are called `Store`, like ObjectStore, SampleStore, etc...

        The difference between `json` and `jsonobj` is subtle. Consider
        storing a complex object. Then there are two ways to do that.
        1. `json`: Store a reference to the object (provided) it is stored and
        2. `jsonobj`: serialize the object and only use references for contained
        objects. All inner objects will always be stored using references.
        The only exception is using nestable. Consider objects that contain
        references to objects of the same type, like e.g. operations in an
        equation (2*3 + 3). Each operation represents a value but each
        operation needs values to operate on. To save such an object you have
        again two options:
        1. `nestable=False`. Store all single objects and always reference
        the contained objects. For an equation that would mean to store several
        objects `op1 = plus(op2, 3), op2 = times(2, 3)`. Since this is correct
        though not intuitive you can also use
        2. `nestable=True`. Store all the serialized objects nested into one
        object (string). For our example this corresponds to
        `plus(times(2,3), 3)`.

        """

        super(ObjectStore, self).__init__()
        self._storage = None
        self.content_class = content_class
        self.cache = NoCache()
        self._free = set()
        self._cached_all = False
        self._created = False
        self._document = None

        self.name = name

        self.attribute_list = {}
        self.cv = {}

        # This will not be stored since its information is contained in the
        # dimension names
        self._dimension_name_store = None

        self.variables = dict()
        self.units = dict()

        self.index = None

        self.proxy_index = WeakValueDictionary()

        if self.content_class is not None \
                and not issubclass(self.content_class, StorableMixin):
            raise ValueError(
                'Content class "%s" must be subclassed from StorableMixin.' %
                self.content_class.__name__)

    def is_created(self):
        return self._created

    def to_dict(self):
        return {
            'content_class': self.content_class,
            'name': self.name
        }

    def check_size(self):
        """
        Perform an update in case the DB has been extended by an external source

        Returns
        -------
        bool
            returns `True` if an update was performed

        """
        if len(self) > len(self.index):
            self.load_indices()
            return True

        return False

    def register(self, storage):
        """
        Associate the object store to a specific storage with a given name

        Parameters
        ----------
        storage : :class:`mongodb.NetCDFPlus`
            the storage to be associated with

        """
        self._storage = storage
        self.name = self.name

        self.index = self.create_uuid_index()
        self._document = storage.db[self.name]

    @staticmethod
    def create_uuid_index():
        return []

    def restore(self):
        self.load_indices()

    def load_indices(self):
        # self.index.clear()
        # self.index.extend(
        self.index = [int(UUID(x)) for x in self._document.distinct('_id')]

    @property
    def storage(self):
        """Return the associated storage object

        Returns
        -------

        :class:`mongodb.NetCDFPlus`
            the referenced storage object
        """

        if self._storage is None:
            raise RuntimeError(
                'A storage needs to be added to this store to be used! '
                'Use .register() to do so.')

        return self._storage

    def __str__(self):
        return repr(self)

    def __repr__(self):

        return 'store.%s[%s] : %s' % (
            self.name,
            self.content_class.__name__ if self.content_class is not None else
            'None/ANY',
            str(len(self)) + ' object(s)'
        )

    @property
    def simplifier(self):
        """
        Return the simplifier instance used to create JSON serialization

        Returns
        -------
        :class:`mongodb.dictify.StorableObjectJSON`
            the simplifier object used in the associated storage

        """
        return self.storage.simplifier

    def set_caching(self, caching):
        """
        Set the caching mode for this store

        Parameters
        ----------
        caching : :class:`mongodb.Cache`

        """
        if caching is None:
            caching = self.default_cache

        if caching is True:
            caching = MaxCache()
        elif caching is False:
            caching = NoCache()
        elif type(caching) is int:
            caching = WeakLRUCache(caching)

        if isinstance(caching, Cache):
            self.cache = caching.transfer(self.cache)

    def idx(self, obj):
        """
        Return the index in this store for a given object

        Parameters
        ----------
        obj : :class:`mongodb.base.StorableMixin`
            the object that can be stored in this store for which its index is
            to be returned

        Returns
        -------
        int or `None`
            The integer index of the given object or `None` if it is not
            stored yet
        """
        return self.index[obj.__uuid__]

    def __iter__(self):
        """
        Add iteration over all elements in the storage
        """
        self.check_size()
        for uuid in list(self.index):
            yield self.load(uuid)

    def __len__(self):
        """
        Return the number of stored objects

        Returns
        -------
        int
            number of stored objects

        """
        if hasattr(self, '_document'):
            if self._document:
                return self._document.count()

        return 0

    def proxy(self, item):
        """
        Return a proxy of a object for this store

        Parameters
        ----------
        item : :py:class:`mongodb.base.StorableMixin`
            or int The item or index that points to an object in this store
            and to which a proxy is requested.

        Returns
        -------

        """
        if item is None:
            return None

        tt = type(item)
        if tt is long:
            idx = item
        elif tt in [str, unicode]:
            if item[0] == '-':
                return None
            idx = int(UUID(item))
        else:
            idx = item.__uuid__

        return LoaderProxy(self, idx)

    def __contains__(self, item):
        if item.__uuid__ in self.index:
            return True

        if self.check_size():
            if item.__uuid__ in self.index:
                return True

        return False

    def __getitem__(self, item):
        """
        Enable numpy style selection of object in the store
        """
        try:
            if type(item) is int:
                if item < 0:
                    item += len(self)
                return self.load(item)
            elif type(item) is str or type(item) is long:
                return self.load(item)
            elif type(item) is list:
                return [self.load(idx) for idx in item]
            elif item is Ellipsis:
                return iter(self)
        except KeyError:
            return None

    def get(self, item):
        try:
            return self[item]
        except KeyError:
            if self.check_size():
                try:
                    return self[item]
                except KeyError:
                    pass

        return None

    def consume_one(self, func=None):
        consumed = None
        while consumed is None and len(self) > 0:
            if func is None:
                one = self.one
            else:

                try:
                    one = next(t for t in self if func(t))
                except StopIteration:
                    break

            idx = one.__uuid__
            erg = self._document.remove({'_id': str(UUID(int=idx))})
            if erg['ok']:
                consumed = one
            else:
                # this means we have a racing condition and the one we found had
                # had been deleted in the meantime
                # just retry and get another
                pass

        if consumed is not None:
            self.index.remove(consumed.__uuid__)
            if consumed.__uuid__ in self.cache:
                del self.cache[consumed.__uuid__]

        return consumed

    def modify_one(self, key, value, update):
        modified = None
        while modified is None and len(self) > 0:

            erg = self._document.find_and_modify(
                query={key: value},
                update={"$set": {key: update}},
                upsert=False
                )

            if erg is not None:
                # success, we got it
                idx = int(UUID(erg['_id']))

                # remove from cache
                if idx in self.cache:
                    del self.cache[idx]

                modified = self.load(idx)

        return modified

    def modify_test_one(self, test_fnc, key, value, update):
        modified = None
        while modified is None and len(self) > 0:
            try:
                found_ones = self._document.find({key: value})
                one = next(t for t in (self.load(int(UUID(f['_id']))) for f in found_ones) if test_fnc(t))

            except StopIteration:
                break

            idx = one.__uuid__

            erg = self._document.find_and_modify(
                query={key: value, '_id': str(UUID(int=idx))},
                update={"$set": {key: update}},
                upsert=False
                )

            if erg is not None:
                # success, we got it

                # remove from cache
                if idx in self.cache:
                    del self.cache[idx]

                modified = self.load(idx)

        return modified

    def _load(self, idx):
        obj = self.storage.simplifier.from_simple_dict(
            self._document.find_one({'_id': str(UUID(int=idx))}))
        obj.__store__ = self
        return obj

    def clear_cache(self):
        """Clear the cache and force reloading"""

        self.cache.clear()
        self._cached_all = False

    def cache_all(self):
        """Load all samples as fast as possible into the cache"""
        if not self._cached_all:
            idxs = range(len(self))
            jsons = self.variables['json'][:]

            [self.add_single_to_cache(i, j) for i, j in zip(
                idxs,
                jsons)]

            self._cached_all = True

    def _save(self, obj):
        dct = self.storage.simplifier.to_simple_dict(obj)
        self._document.insert(dct)
        obj.__store__ = self

    @property
    def last(self):
        """
        Returns the last generated trajectory. Useful to continue a run.

        Returns
        -------
        :py:class:`mongodb.base.StorableMixin`
            the last stored object in this store
        """
        return self.load(len(self) - 1)

    @property
    def first(self):
        """
        Returns the first stored object.

        Returns
        -------
        :py:class:`mongodb.base.StorableMixin`
            the actual first stored object
        """
        return self.load(0)

    @property
    def one(self):
        """
        Returns one random object.

        Returns
        -------
        `StorableMixin`
            the content of the store
        """
        idx = int(UUID(self._document.find_one()['_id']))
        return self.load(idx)

    @property
    def last(self):
        """
        Returns the last saved object.

        This is only accurate to seconds!

        Returns
        -------
        `StorableMixin`
            the content of the store
        """
        idx = int(UUID(self._document.find_one(sort=[("_time", -1)])['_id']))
        return self.load(idx)

    @property
    def first(self):
        """
        Returns the first saved object.

        This is only accurate to seconds!

        Returns
        -------
        `StorableMixin`
            the content of the store
        """
        idx = int(UUID(self._document.find_one(sort=[("_time", 1)])['_id']))
        return self.load(idx)

    def free(self):
        """
        Return the number of the next free index for this store

        Returns
        -------
        index : int
            the number of the next free index in the storage.
            Used to store a new object.
        """

        idx = len(self)

        return idx

    def initialize(self):
        """
        Initialize the associated storage to allow for object storage. Mainly
        creates an index dimension with the name of the object.
        """

        self._created = True

    # ==========================================================================
    # LOAD/SAVE DECORATORS FOR CACHE HANDLING
    # ==========================================================================

    def find_one(self, dct):
        idx = self._document.find_one(dct)['_id']
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
            idx = int(UUID(self._document.find_one({'name': idx})['_id']))

        if type(idx) is long:
            if idx not in self.index:
                self.check_size()
                if idx not in self.index:
                    raise ValueError(
                        'str %s not found in storage' % idx)

        else:
            raise ValueError((
                'indices of type "%s" are not allowed in named storage '
                '(only str and long)') % type(idx).__name__
            )

        # if it is in the cache, return it
        try:
            obj = self.cache[idx]
            logger.debug('Found IDX #' + str(idx) + ' in cache. Not loading!')
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

            logger.debug(
                'Try loading UUID object of type %s and IDX # %d ... DONE' %
                (self.content_class.__name__, idx))

        logger.debug(
            'Finished load object of type %s and IDX # %d ... DONE' %
            (self.content_class.__name__, idx))

        return obj

    @staticmethod
    def reference(obj):
        return obj.__uuid__

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

        # mark as saved so circular dependencies will not cause infinite loops
        n_idx = len(self.index)
        self.index.append(uuid)

        logger.debug('Saving ' + str(type(obj)) + ' using IDX #' + str(uuid))

        try:
            self._save(obj)
            self.cache[uuid] = obj

        except:
            # in case we did not succeed remove the mark as being saved
            del self.index[n_idx]
            raise

        return self.reference(obj)

    def add_single_to_cache(self, idx, json):
        """
        Add a single object to cache by json

        Parameters
        ----------
        idx : int
            the index where the object was stored
        json : str
            json string the represents a serialized version of the stored object
        """

        if idx not in self.cache:
            obj = self.simplifier.from_json(json)

            # self._get_id(idx, obj)

            self.cache[idx] = obj
            self.index[obj.__uuid__] = idx

            return obj
