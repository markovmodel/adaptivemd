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


from collections import OrderedDict
import weakref

__author__ = 'Jan-Hendrik Prinz'


class Cache(object):
    """
    A cache like dict
    """
    @property
    def count(self):
        """
        int : the number of strong references
        int : the number of weak references
        """
        return len(self), 0

    @property
    def size(self):
        """
        int : the maximal number of strong references, -1 if infinite
        int : the maximal number of weak references, -1 if infinite

        """
        return -1, -1

    def __str__(self):
        size = self.count
        maximum = self.size
        return '%s(%d/%d of %s/%s)' % (
            self.__class__.__name__,
            size[0], size[1],
            'Inf' if maximum[0] < 0 else str(maximum[0]),
            'Inf' if maximum[1] < 0 else str(maximum[1])
        )

    def __delitem__(self, key):
        pass

    def __getitem__(self, item):
        raise KeyError("No items")

    def __setitem__(self, key, value):
        pass

    def get(self, item, default=None):
        """
        get value by key if it exists, None else

        Parameters
        ----------
        item : object
            key to select element in cache
        default : object
            return value if item is not present in cache

        Returns
        -------
        object or None
            cached value at key item if present, returns default otherwise
        """
        try:
            return self[item]
        except KeyError:
            return default

    def transfer(self, old_cache):
        """
        Transfer values between caches

        Useful if during run-time a cache is replaced by another instance

        Parameters
        ----------
        old_cache : the cache from which this cache is to be filled

        """
        size = self.size
        if size[0] == -1 or size[1] == -1:
            for key in reversed(list(old_cache)):
                try:
                    self[key] = old_cache[key]
                except KeyError:
                    pass
        else:
            for key in reversed(list(old_cache)[0:size[0] + size[1]]):
                try:
                    self[key] = old_cache[key]
                except KeyError:
                    pass

        return self

    get_silent = get


class NoCache(Cache):
    """
    A virtual cache the contains no elements
    """
    def __init__(self):
        super(NoCache, self).__init__()

    def __getitem__(self, item):
        raise KeyError('No Cache has no items')

    def __contains__(self, item):
        return False

    def __setitem__(self, key, value):
        pass

    def __iter__(self):
        return iter([])

    @property
    def count(self):
        return 0, 0

    @property
    def size(self):
        return 0, 0

    def items(self):
        return []

    def transfer(self, old_cache):
        return self

    def clear(self):
        pass


class MaxCache(dict, Cache):
    """
    A dictionary, can hold infinite strong references
    """
    def __init__(self):
        super(MaxCache, self).__init__()
        Cache.__init__(self)

    @property
    def count(self):
        return len(self), 0

    @property
    def size(self):
        return -1, 0


class LRUCache(Cache):
    """
    Implements a simple Least Recently Used Cache

    Very simple using collections.OrderedDict. The size can be changed during
    run-time
    """

    def __init__(self, size_limit):
        super(LRUCache, self).__init__()
        self._size_limit = size_limit
        self._cache = OrderedDict()

    @property
    def count(self):
        return len(self._cache), 0

    @property
    def size(self):
        return self.size_limit, 0

    @property
    def size_limit(self):
        return self._size_limit

    @size_limit.setter
    def size_limit(self, new_size):
        if new_size < self.size_limit:
            self._check_size_limit()

        self._size_limit = new_size

    def __iter__(self):
        return iter(self._cache)

    def __reversed__(self):
        return reversed(self._cache)

    def __getitem__(self, item):
        obj = self._cache.pop(item)
        self._cache[item] = obj
        return obj

    def __setitem__(self, key, value, **kwargs):
        self._cache[key] = value
        self._check_size_limit()

    def _check_size_limit(self):
        while len(self._cache) > self.size_limit:
            self._cache.popitem(last=False)

    def __contains__(self, item):
        return item in self._cache

    def clear(self):
        self._cache.clear()

    def __len__(self):
        return len(self._cache)


class WeakLRUCache(Cache):
    """
    Implements a cache that keeps weak references to all elements

    In addition it uses a simple Least Recently Used Cache to make sure a
    portion of the last used elements are still present. Usually this
    number is 100.

    """

    def __init__(self, size_limit=100, weak_type='value'):
        """
        Parameters
        ----------
        size_limit : int
            integer that defines the size of the LRU cache. Default is 100.
        """

        super(WeakLRUCache, self).__init__()
        self._size_limit = size_limit
        self.weak_type = weak_type

        if weak_type == 'value':
            self._weak_cache = weakref.WeakValueDictionary()
        elif weak_type == 'key':
            self._weak_cache = weakref.WeakKeyDictionary()
        else:
            raise ValueError("weak_type must be either 'key' or 'value'")

        self._cache = OrderedDict()

    @property
    def count(self):
        return len(self._cache), len(self._weak_cache)

    @property
    def size(self):
        return self._size_limit, -1

    def clear(self):
        self._cache.clear()
        self._weak_cache.clear()

    @property
    def size_limit(self):
        return self._size_limit

    def __getitem__(self, item):
        try:
            obj = self._cache.pop(item)
            self._cache[item] = obj
            return obj
        except KeyError:
            obj = self._weak_cache[item]
            del self._weak_cache[item]
            self._cache[item] = obj
            self._check_size_limit()
            return obj

    @size_limit.setter
    def size_limit(self, new_size):
        if new_size < self.size_limit:
            self._check_size_limit()

        self._size_limit = new_size

    def __setitem__(self, key, value, **kwargs):
        try:
            self._cache.pop(key)
        except KeyError:
            pass

        self._cache[key] = value
        self._check_size_limit()

    def get_silent(self, item):
        """
        Return item from the without reordering the LRU

        Parameters
        ----------
        item : object
            the item index to be retrieved from the cache

        Returns
        -------
        object or None
            the requested object if it exists else None
        """
        if item is None:
            return None

        try:
            return self._cache[item]
        except KeyError:
            try:
                return self._weak_cache[item]
            except KeyError:
                return None

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self._cache) > self.size_limit:
                self._weak_cache.__setitem__(*self._cache.popitem(last=False))

    def __contains__(self, item):
        return item in self._cache or item in self._weak_cache

    def keys(self):
        res = []
        res.extend(self._cache.keys())
        res.extend(self._weak_cache.keys())
        return res

    def values(self):
        res = []
        res.extend(self._cache.values())
        res.extend(self._weak_cache.values())
        return res

    def __len__(self):
        return len(self._cache) + len(self._weak_cache)

    def __iter__(self):
        for key in self.keys():
            yield key

    def __reversed__(self):
        for key in reversed(self._weak_cache):
            yield key

        for key in reversed(self._cache):
            yield key


class WeakValueCache(weakref.WeakValueDictionary, Cache):
    """
    Implements a cache that keeps weak references to all elements
    """

    def __init__(self, *args, **kwargs):
        weakref.WeakValueDictionary.__init__(self, *args, **kwargs)
        Cache.__init__(self)

    @property
    def count(self):
        return 0, len(self)

    @property
    def size(self):
        return 0, -1


class WeakKeyCache(weakref.WeakKeyDictionary, Cache):
    """
    Implements a cache that keeps weak references to all elements
    """

    @property
    def count(self):
        return 0, len(self)

    @property
    def size(self):
        return 0, -1
