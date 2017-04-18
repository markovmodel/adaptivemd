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

"""
Bundle - A set-enhancement to add filtering and store handling capabilities

A bundle can be accessed as a normal set using iteration. You can add objects
using `.add(item)` if the bundle is not a view

Examples
--------
Some basic functions

>>> bundle = Bundle(['10', '20', 1, 2, 3])
>>> str_view = bundle.c(basestring)  # only how strings
>>> print list(str_view)  # ['10', '20']
>>> fnc_view = bundle.v(lambda x: int(x) < 3)
>>> print list(fnc_view) # [1, 2]

Some `File` specific functions

>>> import adaptivemd as amd
>>> bundle = Bundle([amd.File('0.dcd'), amd.File('a.pdb')])
>>> file_view = bundle.f('*.dcd')
>>> print list(file_view)  # [File('0.dcd')]

Logic operations produce view on the resulting bundle

>>> and_bundle = str_view & fnc_view
>>> print list(and_bundle)  # []
>>> and_bundle = str_view | fnc_view
>>> print list(and_bundle)  # [1, 2, '10', '20']

A `StorableBundle` is attached to a mongodb store (a stored object list).
Adding will append the object to the store if not stored yet. All iteration
and views will always be kept synced with the DB store content.

>>> p = amd.Project('test-project')
>>> store = StoredBundle()  # new bundle
>>> store.set_store(p.storage.trajectories)  # attach to DB
>>> print list(store)  # show all trajectories
>>> len_store = store.v(lambda x: len(x) > 10)  # all trajs with len > 10
>>> print list(len_store)

Set do not have ordering so some functions do not make sense. As long as
you are working with storable objects (subclassed from `StorableMixin`)
you have some time-ordering (accurate to seconds)

>>> print store.first  # get the earlist created object
>>> print store.one    # get one (any) single object
>>> print store.last   # get the last created object

A bundle is mostly meant to work with storable objects (but does not have to)
To simplify access to certain attributes or apply function to all members you
can use the `.all` attribute and get a _delegator_ that will apply and
attribute or method to all objects

>>> print len_store.all.length  # print all lengths of all objects in len_store
>>> print store.all.path  # print all path of all trajectories
>>> # call `.execute('shutdown') on all workers in the `.workers` bundle
>>> print p.workers.all.execute('shutdown')

"""

import fnmatch
import random

import logging
logger = logging.getLogger(__name__)


class BaseBundle(object):
    """
    BaseClass for Bundle functionality a special set of storable objects
    """
    def __iter__(self):
        return iter([])

    def __and__(self, other):
        if isinstance(other, BaseBundle):
            return AndBundle(self, other)

        return NotImplemented

    def __len__(self):
        return len([None for _ in self])

    def __or__(self, other):
        if isinstance(other, BaseBundle):
            return OrBundle(self, other)

        return NotImplemented

    def __getitem__(self, item):
        """
        Get by name

        Parameters
        ----------
        item : str
            in this case it acts like a dict and you can ask for one object
            with a certain name

        Returns
        -------
        object

        """
        for f in self:
            if hasattr(f, 'name') and f.name == item:
                return f

    def c(self, cls):
        """
        Return a view bundle on all entries that are instances of a class

        Parameters
        ----------
        cls : `type`
            a class to be filtered by

        Returns
        -------
        `ViewBundle`
            the read-only bundle showing filtered entries

        """
        return ViewBundle(self, lambda x: isinstance(x, cls))

    def f(self, pattern):
        """
        Return a view bundle on all entries that match a location pattern

        Works only when all objects are of type `File`

        Parameters
        ----------
        pattern : str
            a string CL pattern using wildcards to match a filename

        Returns
        -------
        `ViewBundle`
            the read-only bundle showing filtered entries

        """
        return ViewBundle(self, lambda x: fnmatch.fnmatch(x.location, pattern))

    def sorted(self, key):
        """
        Return a view bundle where all entries are sorted by a given key attribute

        Parameters
        ----------
        key : function
            a function to compute the key to be sorted by

        Returns
        -------
        `ViewBundle`
            the read-only bundle showing sorted entries

        """
        return SortedBundle(self, key)

    def v(self, fnc):
        """
        Return a view bundle on all entries that are filtered by a function

        Parameters
        ----------
        fnc : function
            a function to be used for filtering

        Returns
        -------
        `ViewBundle`
            the read-only bundle showing filtered entries

        """
        return ViewBundle(self, fnc)

    def pick(self):
        """
        Pick a random element

        Returns
        -------
        object or None
            a random object if bundle is not empty

        """
        if self:
            return random.choice(tuple(self))
        else:
            return None

    def __str__(self):
        return '<%s for with %d file(s) @ %s>' % (
            self.__class__.__name__, len(self), hex(id(self)))

    def __contains__(self, item):
        for o in self:
            if o == item:
                return True

        return False

    @property
    def one(self):
        """
        Return one element from the list

        Use only if you just need one and do not care which one it is

        Returns
        -------
        object
            one object (there is no guarantee that this will always be the same element)

        """
        if len(self) > 0:
            return next(iter(self))
        else:
            return None

    @property
    def all(self):
        """
        Return a Delegator that will apply attribute and function call to all bundle elements

        Returns
        -------
        `BundleDelegator`
            the delegator object to map to all elements in the bundle
        """
        return BundleDelegator(self)


class Bundle(BaseBundle):
    """
    A container of objects
    """

    def __init__(self, iterable=None):
        super(Bundle, self).__init__()

        if iterable is None:
            self._set = set()
        elif isinstance(iterable, set):
            self._set = iterable
        else:
            self._set = set(iterable)

    def __len__(self):
        if self._set is not None:
            return len(self._set)
        else:
            return 0

    def update(self, iterable):
        """
        Add multiple items to the bundle at once

        Parameters
        ----------
        iterable : Iterable
            the items to be added

        """
        map(self.add, iterable)

    def add(self, item):
        """
        Add a single item to the bundle

        Parameters
        ----------
        item : object
        """
        if self._set is not None:
            self._set.add(item)

    def __iter__(self):
        if self._set is not None:
            return iter(self._set)
        else:
            return iter([])


class LogicBundle(BaseBundle):
    """
    Implement simple and and or logic for bundles
    """
    def __init__(self, bundle1, bundle2):
        super(LogicBundle, self).__init__()
        self.bundle1 = bundle1
        self.bundle2 = bundle2


class AndBundle(LogicBundle):
    """
    And logic
    """
    def __iter__(self):
        return iter(set(self.bundle1) & set(self.bundle2))


class OrBundle(LogicBundle):
    """
    Or logic
    """
    def __iter__(self):
        return iter(set(self.bundle1) | set(self.bundle2))


class ViewBundle(BaseBundle):
    """
    A view on a bundle where object are filtered by a bool function
    """
    def __init__(self, bundle, view):
        super(ViewBundle, self).__init__()
        self.bundle = bundle
        self.view = view

    def __iter__(self):
        for o in self.bundle:
            if self.view(o):
                yield o


class SortedBundle(BaseBundle):
    """
    Sorted view of a bundle
    """
    def __init__(self, bundle, key):
        self.bundle = bundle
        self.key = key

    def __iter__(self):
        return iter(sorted(self.bundle, key=self.key))

    @property
    def first(self):
        """
        object
            Return the first of the sorted elements

        """
        return next(iter(self))


class BundleDelegator(object):
    """
    Delegate an attribute call to all elements in a bundle
    """
    def __init__(self, bundle):
        self._bundle = bundle

    def __getattr__(self, item):
        one = self._bundle.one
        if hasattr(one, item):
            attr = getattr(one, item)
            if callable(attr):
                return FunctionDelegator(self._bundle, item)
            else:
                return [getattr(x, item) for x in self._bundle]
        else:
            AttributeError('Not all objects have attribute `%s`' % item)


class FunctionDelegator(object):
    """
    Delegate a function call to all elements in a bundle
    """
    def __init__(self, bundle, item):
        self._bundle = bundle
        self._item = item

    def __call__(self, *args, **kwargs):
        return [getattr(x, self._item)(*args, **kwargs) for x in self._bundle]


class StoredBundle(Bundle):
    """
    A stored bundle in a mongodb

    This is a useful wrapper to turn a store of the MongoDB into a bundle of objects.
    Adding files will store new elements. The bundle is always in sync with the DB.

    """
    def __init__(self):
        super(StoredBundle, self).__init__()
        self._set = None

    def set_store(self, store):
        """
        Set the used store

        Parameters
        ----------
        store : `ObjectStore`
            a mongodb store that contains the elements in the bundle

        """
        self._set = store
        return self

    def close(self):
        """
        Close the connection to the bundle.

        A not connected bundle will have no entries and none can be added

        """
        self._set = None

    def add(self, item):
        """
        Add an element to the bundle

        Parameters
        ----------
        item : object
            the item to be added to the bundle

        """
        if self._set is not None and item not in self._set:
            logger.info('Added file of type `%s`' % item.__class__.__name__)
            self._set.save(item)

    @property
    def last(self):
        """
        Return the entry with the latest timestamp

        Returns
        -------
        object
            the latest object

        """
        if self._set is not None:
            return self._set.last

    @property
    def first(self):
        """
        Return the entry with the earliest timestamp

        Returns
        -------
        object
            the earliest object

        """
        if self._set is not None:
            return self._set.first

    def __getitem__(self, item):
        # this is faster for storages
        if self._set is not None:
            return self._set[item]

    def consume_one(self):
        """
        Picks and removes one (random) element in one step.

        Returns
        -------
        `StorableMixin` or None
            The deleted object if possible otherwise None
        """
        if self._set is not None:
            return self._set.consume_one()

        return None

    def find_all_by(self, key, value):
        """
        Return all elements from the bundle where its key matches value

        Parameters
        ----------
        key : str
            the attribute
        value : object
            the value to match against using `==`

        Returns
        -------
        list of `StorableMixin`
            a list of objects in the bundle that match the search
        """

        if self._set is not None:
            return [x for x in self._set if getattr(x, key) == value]
