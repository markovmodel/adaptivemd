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


import inspect
import logging
import time
import uuid

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
        """
        Create a new unique ID
        Returns
        -------
        long
            the unique number for an object in the project

        """
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
        """
        Attach a .name property to an object

        Parameters
        ----------
        name : str
            the name of the object

        Returns
        -------
        self
            the object itself for chaining

        """
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
            the integer index for the object of it exists or None else

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
        Reconstruct an object from a dictionary representation

        Parameters
        ----------
        dct : dict
            the dictionary containing a state representation of the class.

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
    """
    Create a to_dict function from a list of attributes

    Parameters
    ----------
    keys_to_store : list of str
        the attributes used in { attr: getattr(self, attr) }

    Returns
    -------
    function
        the `to_dict` function

    """
    def to_dict(self):
        return {key: getattr(self, key) for key in keys_to_store}

    return to_dict
