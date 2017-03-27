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


import functools
import weakref

from base import StorableMixin


# =============================================================================
# Loader Proxy
# =============================================================================

class LoaderProxy(object):
    """
    A proxy that loads an underlying object if attributes are accessed
    """
    __slots__ = ['_subject', '_idx', '_store', '__weakref__']

    def __init__(self, store, idx):
        self._idx = idx
        self._store = store
        self._subject = None

    @property
    def __subject__(self):
        if self._subject is not None:
            obj = self._subject()
            if obj is not None:
                return obj

        ref = self._load_()

        if ref is None:
            return None

        self._subject = weakref.ref(ref)
        return ref

    def __eq__(self, other):
        if self is other:
            return True

        if hasattr(other, '__uuid__'):
            return self.__uuid__ == other.__uuid__

        return NotImplemented

    def __getitem__(self, item):
        return self.__subject__[item]

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self._idx)

    def __len__(self):
        return len(self.__subject__)

    @property
    def __class__(self):
        return self._store.content_class

    @property
    def __uuid__(self):
        return self._idx

    def __getattr__(self, item):
        return getattr(self.__subject__, item)

    def _load_(self):
        """
        Call the loader and get the referenced object
        """
        try:
            return self._store[self._idx]
        except KeyError:
            if type(self._idx) is int:
                raise RuntimeWarning(
                    'Index %s is not in store. This should never happen!' %
                    self._idx)
            else:
                raise RuntimeWarning(
                    'Object %s is not in store. Attach it using fallbacks.' %
                    self._idx)


class DelayedLoader(object):
    """
    Descriptor class to handle proxy objects in attributes

    If a proxy is stored in an attribute then the full object will be returned
    """
    def __get__(self, instance, owner):
        if instance is not None:
            obj = instance._lazy[self]
            if hasattr(obj, '_idx'):
                return obj.__subject__
            else:
                return obj
        else:
            return self

    def __set__(self, instance, value):
        instance._lazy[self] = value


def lazy_loading_attributes(*attributes):
    """
    Set attributes in the decorated class to be handled as lazy loaded objects.

    An attribute that is added here will be turned into a special descriptor
    that will dynamically load an objects if it is represented internally as a
    LoaderProxy object and will return the real object, not the proxy!

    The second thing you can do is that saving using the `.write()` command will
    automatically remove the real object and turn the stored object into
    a proxy

    Notes
    -----
    This decorator will obfuscate the __init__ signature in Python 2.
    This is fixed in Python 3.4+

    """
    def _decorator(cls):
        for attr in attributes:
            setattr(cls, attr, DelayedLoader())

        _super_init = cls.__init__

        code = 'def _init(self, %s):'

        source_code = '\n'.join(code)
        cc = compile(source_code, '<string>', 'exec')
        exec cc in locals()

        @functools.wraps(cls.__init__)
        def _init(self, *args, **kwargs):
            self._lazy = {}
            _super_init(self, *args, **kwargs)

        cls.__init__ = _init
        return cls

    return _decorator
