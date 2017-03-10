import inspect
import logging
import uuid
import time
import weakref

logger = logging.getLogger(__name__)


class StorableMixin(object):
    """Mixin that allows objects of the class to to be stored using netCDF+

    """

    _base = None
    _args = None
    _ignore = False
    _find_by = []

    INSTANCE_UUID = list(uuid.uuid1().fields[:-1])
    CREATION_COUNT = 0L
    ACTIVE_LONG = int(uuid.UUID(
            fields=tuple(
                INSTANCE_UUID +
                [CREATION_COUNT]
            )
        ))

    @staticmethod
    def get_uuid():
        StorableMixin.ACTIVE_LONG += 2
        return StorableMixin.ACTIVE_LONG

    def __init__(self):
        # set the universal ID
        self.__uuid__ = StorableMixin.get_uuid()
        # set the creation time
        self.__time__ = int(time.time())
        self.__store__ = None

    def __eq__(self, other):
        if isinstance(other, StorableMixin):
            return self.__uuid__ == other.__uuid__

        return NotImplemented

    def named(self, name):
        self.name = name
        return self

    def idx(self, store):
        """
        Return the index which is used for the object in the given store.

        Once you store a storable object in a store it gets assigned a unique
        number that can be used to retrieve the object back from the store. This
        function will ask the given store if the object is stored if so what
        the used index is.

        Parameters
        ----------
        store : :class:`ObjectStore`
            the store in which to ask for the index

        Returns
        -------
        int or None
            the integer index for the object of it exists or `None` else

        """
        if hasattr(store, 'index'):
            return store.index.get(self, None)
        else:
            return store.idx(self)

    @property
    def cls(self):
        """
        Return the class name as a string

        Returns
        -------
        str
            the class name

        """
        return self.__class__.__name__

    @classmethod
    def base(cls):
        """
        Return the most parent class actually derived from StorableMixin

        Important to determine which store should be used for storage

        Returns
        -------
        type
            the base class
        """
        if cls._base is None:
            if cls is not StorableMixin:
                if StorableMixin in cls.__bases__:
                    cls._base = cls
                else:
                    if hasattr(cls.__base__, 'base'):
                        cls._base = cls.__base__.base()
                    else:
                        cls._base = cls

        return cls._base

    def __hash__(self):
        return hash(self.__uuid__)

    @property
    def base_cls_name(self):
        """
        Return the name of the base class

        Returns
        -------
        str
            the string representation of the base class

        """
        return self.base().__name__

    @property
    def base_cls(self):
        """
        Return the base class

        Returns
        -------
        type
            the base class

        See Also
        --------
        :func:`base()`

        """
        return self.base()

    @classmethod
    def descendants(cls):
        """
        Return a list of all subclassed objects

        Returns
        -------
        list of type
            list of subclasses of a storable object
        """
        return cls.__subclasses__() + \
            [g for s in cls.__subclasses__() for g in s.descendants()]

    @staticmethod
    def objects():
        """
        Returns a dictionary of all storable objects

        Returns
        -------
        dict of str : type
            a dictionary of all subclassed objects from StorableMixin.
            The name points to the class
        """
        subclasses = StorableMixin.descendants()

        return {subclass.__name__: subclass for subclass in subclasses}

    @classmethod
    def args(cls):
        """
        Return a list of args of the `__init__` function of a class

        Returns
        -------
        list of str
            the list of argument names. No information about defaults is
            included.

        """
        try:
            args = inspect.getargspec(cls.__init__)
        except TypeError:
            return []
        return args[0]

    _excluded_attr = []
    _included_attr = []
    _exclude_private_attr = True
    _restore_non_initial_attr = True
    _restore_name = True

    def to_dict(self):
        """
        Convert object into a dictionary representation

        Used to convert the dictionary into JSON string for serialization

        Returns
        -------
        dict
            the dictionary representing the (immutable) state of the object

        """
        excluded_keys = ['idx', 'json', 'identifier']
        keys_to_store = {
            key for key in self.__dict__
            if key in self._included_attr or (
                key not in excluded_keys and
                key not in self._excluded_attr and
                not (key.startswith('_') and self._exclude_private_attr)
            )
        }
        return {
            key: self.__dict__[key] for key in keys_to_store
        }

    @classmethod
    def from_dict(cls, dct):
        """
        Reconstruct an object from a dictionary representaiton

        Parameters
        ----------
        dct : dict
            the dictionary containing a state representaion of the class.

        Returns
        -------
        :class:`StorableMixin`
            the reconstructed storable object
        """
        if dct is None:
            dct = {}

        if hasattr(cls, 'args'):
            args = cls.args()
            init_dct = {key: dct[key] for key in dct if key in args}
            try:
                obj = cls(**init_dct)

                if cls._restore_non_initial_attr:
                    non_init_dct = {
                        key: dct[key] for key in dct if key not in args}

                    if len(non_init_dct) > 0:
                        for key, value in non_init_dct.iteritems():
                            setattr(obj, key, value)

                return obj

            except TypeError as e:
                if hasattr(cls, 'args'):
                    err = (
                        'Could not reconstruct the object of class `%s`. '
                        '\nStored parameters: %s \n'
                        '\nCall parameters: %s \n'
                        '\nSignature parameters: %s \n'
                        '\nActual message: %s'
                    ) % (
                        cls.__name__,
                        str(dct),
                        str(init_dct),
                        str(cls.args),
                        str(e)
                    )
                    raise TypeError(err)
                else:
                    raise

        else:
            return cls(**dct)


def create_to_dict(keys_to_store):
    def to_dict(self):
        return {key: getattr(self, key) for key in keys_to_store}

    return to_dict


class SyncVariable(object):
    """
    A DB synced variable
    """
    def __init__(self, name, fix_fnc=None):
        self.name = name
        self.fix_fnc = fix_fnc
        self.values = weakref.WeakKeyDictionary()

    def _idx(self, instance):
        return str(uuid.UUID(int=instance.__uuid__))

    def _update(self, store, idx):
        if store is not None:
            return store._document.find_one(
                {'_id': idx}).get(self.name)

        return None

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            if self.fix_fnc:
                val = self.values.get(instance.__uuid__)
                if val is not None and self.fix_fnc(val):
                    return val

            if instance.__store__ is not None:
                idx = self._idx(instance)
                value = self._update(instance.__store__, idx)
                self.values[instance.__uuid__] = value
                return value
            else:
                return self.values.get(instance.__uuid__)

    def __set__(self, instance, value):
        if self.fix_fnc:
            val = self.values.get(instance.__uuid__)
            if val is not None and self.fix_fnc(val):
                return

        if instance.__store__ is not None:
            idx = str(uuid.UUID(int=instance.__uuid__))
            instance.__store__._document.find_and_modify(
                query={'_id': idx},
                update={"$set": {self.name: value}},
                upsert=False
                )

        self.values[instance.__uuid__] = value


class NoneOrValueSyncVariable(SyncVariable):
    """
    Variable that can be set once
    """

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            if self.values.get(instance.__uuid__) is None:
                idx = self._idx(instance)
                value = self._update(instance.__store__, idx)
                self.values[instance.__uuid__] = value
                return value

            return self.values.get(instance.__uuid__)

    def __set__(self, instance, value):
        if self.values.get(instance.__uuid__) is None and value is not None:
            if instance.__store__ is not None:
                idx = self._idx(instance)
                instance.__store__._document.find_and_modify(
                    query={'_id': idx, self.name: None},
                    update={"$set": {self.name: value}},
                    upsert=False
                    )
                value = self._update(instance.__store__, idx)

            self.values[instance.__uuid__] = value


class IncreasingNumericSyncVariable(SyncVariable):
    """
    Variable that can be set once
    """

    def __set__(self, instance, value):
        val = self.values.get(instance.__uuid__)

        if self.fix_fnc:
            if val is not None and self.fix_fnc(val):
                return val

        if value > val:
            if instance.__store__ is not None:
                idx = self._idx(instance)
                current = self._update(instance.__store__, idx)
                while value > current:
                    instance.__store__._document.find_and_modify(
                        query={'_id': idx, self.name: current},
                        update={"$set": {self.name: value}},
                        upsert=False
                    )
                    current = self._update(instance.__store__, idx)

                value = current

            self.values[instance.__uuid__] = value


class ObjectSyncVariable(SyncVariable):
    def __init__(self, name, store, fix_fnc=None):
        super(ObjectSyncVariable, self).__init__(name, fix_fnc)
        self.store = store

    def _update(self, store, idx):
        if store is not None:
            data = store._document.find_one(
                {'_id': idx})[self.name]
            if data is None:
                return None
            else:
                obj_idx = int(uuid.UUID(data['_hex_uuid']))
                return getattr(store.storage, self.store).load(obj_idx)

    def __set__(self, instance, value):
        if instance.__store__ is not None:
            if self.fix_fnc:
                val = self.values.get(instance.__uuid__)
                if val is not None and self.fix_fnc(val):
                    return val

            idx = self._idx(instance)
            if value is not None:
                instance.__store__._document.find_and_modify(
                    query={'_id': idx},
                    update={"$set": {self.name: {
                        '_hex_uuid': self._idx(value),
                        '_store': self.store}}},
                    upsert=False
                    )
            else:
                instance.__store__._document.find_and_modify(
                    query={'_id': idx},
                    update={"$set": {self.name: None}},
                    upsert=False
                    )

        self.values[instance.__uuid__] = value
