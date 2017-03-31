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

# part of the code below was taken from `openpathsampling` see
# <http://www.openpathsampling.org> or
# <http://github.com/openpathsampling/openpathsampling
# for details and license


import abc
import logging
from collections import OrderedDict
from dictify import UUIDObjectJSON
from object import ObjectStore

from pymongo import MongoClient

logger = logging.getLogger(__name__)


class MongoDBStorage(object):
    """
    Extension of the pymongo wrapper for easier storage of python objects
    """
    _db_url = 'mongodb://localhost:27017/'

    @property
    def version(self):
        import version
        return version.short_version

    @property
    def objects(self):
        """
        Return a dictionary of all objects stored.

        """
        return self._stores

    def find_store(self, obj):
        """
        Return the default store used for an storable object

        Parameters
        ----------
        obj : :class:`mongodb.StorableMixin`
            the storable object to be tested

        Returns
        -------
        :class:`mongodb.ObjectStore`
            the store that is used by default to store the given storable obj
        """

        if type(obj) is type or type(obj) is abc.ABCMeta:
            if obj not in self._obj_store:
                raise ValueError(
                    'Objects of class "%s" are not storable in this store.' %
                    obj.__name__)

            return self._obj_store[obj]
        else:
            if obj.__class__ not in self._obj_store:
                raise ValueError(
                    'Objects of class "%s" are not storable in this store.' %
                    obj.__class__.__name__)

            return self._obj_store[obj.__class__]

    def update_storable_classes(self):
        """
        Update the internal list of all objects that are subclassed from StorableMixin

        If you create your own subclass of a storable object then you need to call
        this function to update the list so that you can load and save instances of
        your new class

        """
        self.simplifier.update_class_list()

    def __init__(self, filename, mode=None):
        """
        Create a mongodb storage for complex objects

        Parameters
        ----------
        filename : string
            name of the mongodb database
        mode : str
            the mode of file creation, one of 'w' (write), 'a' (append) or
            'r' (read-only) None, which will append any existing files
            (equal to append), is the default.

        Notes
        -----
        You can safely open a storage from multiple instances. These will cross update.

        """

        if mode is None:
            mode = 'a'

        self.mode = mode

        self._client = MongoClient(self._db_url)
        self._db_name = 'storage-' + filename

        self.filename = filename

        # this can be set to false to re-store proxies from other stores
        self.exclude_proxy_from_other = False

        super(MongoDBStorage, self).__init__()

        self._setup_class()

        if mode == 'w':
            logger.info("Setup netCDF file and create variables")

            self._client.drop_database(self._db_name)
            self.db = self._client[self._db_name]
            self._create_simplifier()

            # create the store that holds stores
            store_stores = ObjectStore('stores', ObjectStore)
            self.register_store(store_stores)
            self.stores.initialize()
            self.stores.set_caching(True)

            # this will create all variables in the storage for all new
            # added stores this is often already call inside of _initialize.
            # If not we just make sure
            self.finalize_stores()

            logger.info("Finished setting up netCDF file")

        elif mode == 'a' or mode == 'r+' or mode == 'r':
            logger.debug("Restore the dict of units from the storage")

            self.db = self._client[self._db_name]

            # self.check_version()
            self._create_simplifier()

            # open the store that contains all stores
            self.register_store(ObjectStore('stores', ObjectStore))
            self.stores.set_caching(True)

            self.stores.restore()

            # register all stores that are listed in self.stores

            for store in self.stores:
                self.register_store(store)
                store.register(self)

            self._restore_storages()

            # only if we have a new style file
            if hasattr(self, 'attributes'):
                for attribute, store in zip(
                        self.attributes,
                        self.attributes.vars['cache']
                ):
                    key_store = self.attributes.key_store(attribute)
                    key_store.attribute_list[attribute] = store

    def close(self):
        """
        Close the DB connection

        """
        self._client.close()

    def _create_simplifier(self):
        self.simplifier = UUIDObjectJSON(self)

    @classmethod
    def list_storages(cls):
        c = MongoClient(cls._db_url)
        names = c.database_names()
        c.close()
        return [n[8:] for n in names if n.startswith('storage-')]

    @classmethod
    def delete_storage(cls, name):
        c = MongoClient(cls._db_url)
        c.drop_database('storage-' + name)
        c.close()

    @staticmethod
    def _cmp_version(v1, v2):
        q1 = v1.split('-')[0].split('.')
        q2 = v2.split('-')[0].split('.')
        for v1, v2 in zip(q1, q2):
            if int(v1) > int(v2):
                return +1
            elif int(v1) < int(v2):
                return -1

        return 0

    def check_version(self):
        try:
            s1 = self.getncattr('ncplus_version')
        except AttributeError:
            logger.info(
                'Using mongodb Pre 1.0 version. '
                'No version detected using 0.0.0')
            s1 = '0.0.0'

        s2 = self._mongodb_version_

        cp = self._cmp_version(s1, s2)

        if cp != 0:
            logger.info('Loading different mongodb version. '
                        'Installed version is '
                        '%s and loaded version is %s' % (s2, s1))
            if cp > 0:
                logger.info(
                    'Loaded version is newer consider upgrading your '
                    'conda package!')
            else:
                logger.info(
                    'Loaded version is older. Should be no problem other then '
                    'missing features and information')

    def write_meta(self):
        pass

    def _setup_class(self):
        """
        Sets the basic properties for the storage
        """
        self._stores = OrderedDict()
        self._objects = {}
        self._obj_store = {}
        self._storages_base_cls = {}

    def create_store(self, store, register_attr=True):
        """
        Create a special variable type `obj.name` that can hold storable objects

        Parameters
        ----------
        store : :class:`mongodb.ObjectStore`
            the store to be added to this storage
        register_attr : bool
            if True the store will be added to the storage as an
             attribute with name `name`

        """
        self.register_store(store, register_attr=register_attr)
        self.stores.save(store)

    def finalize_stores(self):
        """
        Run initializations for all added stores.

        This will make sure that all previously added stores are now usable.
        If you add more stores you need to call this again. The reason this is
        done at all is that stores might reference each other and so no
        unique order of creation can be found. Thus you first create stores
        with all their dependencies and then finalize all of them together.
        """
        for store in self._stores.values():
            if not store.is_created():
                logger.info("Initializing store '%s'" % store.name)
                store.initialize()

        for store in self._stores.values():
            if not store.is_created():
                logger.info("Initializing store '%s'" % store.name)
                store.initialize()

        self.simplifier.update_class_list()

    def register_store(self, store, register_attr=True):
        """
        Add a object store to the file

        An object store is a special type of variable that allows to store
        python objects

        Parameters
        ----------
        store : :class:`mongodb.ObjectStore`
            instance of the object store
        register_attr : bool
            if set to false the store will not be accesible as an attribute.
            True is the default.
        """
        name = store.name
        store.register(self)

        if register_attr:
            if hasattr(self, name):
                raise ValueError('Attribute name %s is already in use!' % name)

            setattr(self, store.name, store)

        self._stores[name] = store

        if store.content_class is not None:
            self._objects[store.content_class] = store

            self._obj_store[store.content_class] = store
            self._obj_store.update(
                {cls: store for cls in store.content_class.descendants()})

    def __repr__(self):
        return "Storage @ '" + self.filename + "'"

    def __getattr__(self, item):
        try:
            return self.__dict__[item]
        except KeyError:
            return self.__class__.__dict__[item]

    def __setattr__(self, key, value):
        self.__dict__[key] = value

    def _init_storages(self):
        """
        Run the initialization on all added classes

        Notes
        -----
        Only runs when the storage is created.
        """

        for storage in self._stores.values():
            storage.initialize()

        self.update_delegates()

    def _restore_storages(self):
        """
        Run the restore method on all added classes

        Notes
        -----
        Only runs when an existing storage is opened.
        """

        for storage in self._stores.values():
            storage.restore()
            storage._created = True

    def list_stores(self):
        """
        Return a list of registered stores

        Returns
        -------
        list of str
            list of stores that can be accessed using `storage.[store]`
        """
        return [store.name for store in self._stores.values()]

    def list_storable_objects(self):
        """
        Return a list of storable object base classes

        Returns
        -------
        list of type
            list of base classes that can be stored using `storage.save(obj)`
        """
        return [
            store.content_class
            for store in self.objects.values()
            if store.content_class is not None]

    def save(self, obj):
        """
        Save a storable object into the correct Storage in the netCDF file

        Parameters
        ----------
        obj : :class:`StorableMixin`
            the object to store

        Returns
        -------
        str
            the class name of the BaseClass of the stored object, which is
            needed when loading the object to identify the correct storage
        """

        if type(obj) is list:
            # a list of objects will be stored one by one
            return [self.save(part) for part in obj]

        elif type(obj) is tuple:
            # a tuple will store all parts
            return [self.save(part) for part in obj]

        elif obj.__class__ in self._obj_store:
            # to store we just check if the base_class is present in the
            # storages also we assume that if a class has no base_cls
            store = self.find_store(obj)
            return store, obj.__uuid__, store.save(obj)

        # Could not save this object.
        raise RuntimeWarning("Objects of type '%s' cannot be stored!" %
                             obj.__class__.__name__)

    def __contains__(self, item):
        if type(item) is list:
            # a list of objects will be stored one by one
            return [part in self for part in item]

        elif type(item) is tuple:
            # a tuple will store all parts
            return tuple([part in self for part in item])

        elif item.__class__ in self._obj_store:
            # to store we just check if the base_class is present in the
            # storages also we assume that if a class has no base_cls
            store = self.find_store(item)
            return item in store

        return False

    def load(self, uuid):
        """
        Load an object from the storage

        Parameters
        ----------
        uuid : uuid.UUID
            the uuid to be loaded

        Returns
        -------
        :class:`mongodb.StorableMixin`
            the object loaded from the storage

        Notes
        -----
        this only works in storages with uuids otherwise load directly from the
        sub-stores
        """

        for store in self.objects.values():
            if uuid in store.index:
                return store[uuid]

        # need to update
        for store in self.objects.values():
            store.check_size()
            if uuid in store.index:
                return store[uuid]

        # nothing found.
        raise KeyError("UUID %s not found in storage" % uuid)

    def cache_image(self):
        """
        Return an dict containing information about all caches

        Returns
        -------
        dict
            a nested dict containing information about the number and types of
            cached objects
        """
        image = {
            'weak': {},
            'strong': {},
            'total': {},
            'file': {},
            'index': {}
        }

        total_strong = 0
        total_weak = 0
        total_file = 0
        total_index = 0

        for name, store in self.objects.iteritems():
            size = store.cache.size
            count = store.cache.count
            profile = {
                'count': count[0] + count[1],
                'count_strong': count[0],
                'count_weak': count[1],
                'max': size[0],
                'size_strong': size[0],
                'size_weak': size[1],
            }
            total_strong += count[0]
            total_weak += count[1]
            total_file += len(store)
            total_index += len(store.index)
            image[name] = profile
            image['strong'][name] = count[0]
            image['weak'][name] = count[1]
            image['total'][name] = count[0] + count[1]
            image['file'][name] = len(store)
            image['index'][name] = len(store.index)

        image['full'] = total_weak + total_strong
        image['total_strong'] = total_strong
        image['total_weak'] = total_weak
        image['file'] = total_file
        image['index'] = total_index

        return image
