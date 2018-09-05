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
from __future__ import absolute_import


from .base import StorableMixin, create_to_dict
from .syncvar import SyncVariable, ObjectSyncVariable, JSONDataSyncVariable
from .cache import WeakKeyCache, WeakLRUCache, WeakValueCache, MaxCache, \
    NoCache, Cache, LRUCache
from .dictify import ObjectJSON, UUIDObjectJSON
from .mongodb import MongoDBStorage

from .object import ObjectStore

from .proxy import DelayedLoader, lazy_loading_attributes, LoaderProxy

from .file import FileStore, DataDict
