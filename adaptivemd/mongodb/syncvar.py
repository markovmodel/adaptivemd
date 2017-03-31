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


import uuid

from dictify import ObjectJSON


class SyncVariable(object):
    def __init__(self, name, fix_fnc=None):
        self.name = name
        self.fix_fnc = fix_fnc
        self.key = '_' + self.name + '_'

    @staticmethod
    def _idx(instance):
        return str(uuid.UUID(int=instance.__uuid__))

    @staticmethod
    def _hex(instance):
        return hex(instance.__uuid__)

    def _update(self, store, idx):
        if store is not None:
            return store._document.find_one(
                {'_id': idx})

        return None
    
    def read(self, instance):
        try:
            return getattr(instance, self.key)
        except AttributeError:
            return None
        
    def write(self, instance, v):
        setattr(instance, self.key, v)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            if self.fix_fnc:
                val = self.read(instance)
                if val is not None and self.fix_fnc(val):
                    return val

            if instance.__store__ is not None:
                idx = self._idx(instance)
                dct = self._update(instance.__store__, idx)
                if dct and self.name in dct:
                    value = dct[self.name]
                    self.write(instance, value)
                    return value

            return self.read(instance)

    def __set__(self, instance, value):
        if instance.__store__ is not None:
            if self.fix_fnc:
                val = self.read(instance)
                if val is not None and self.fix_fnc(val):
                    return

            idx = str(uuid.UUID(int=instance.__uuid__))
            instance.__store__._document.find_and_modify(
                query={'_id': idx},
                update={"$set": {self.name: value}},
                upsert=False
                )

        self.write(instance, value)


# class NoneOrValueSyncVariable(SyncVariable):
#     """
#     Variable that can be set once
#     """
#
#     def __get__(self, instance, owner):
#         if instance is None:
#             return self
#         else:
#             if self.read(instance) is None:
#                 idx = self._idx(instance)
#                 value = self._update(instance.__store__, idx)
#                 self.write(instance, value)
#                 return value
#
#             return self.read(instance)
#
#     def __set__(self, instance, value):
#         if self.read(instance) is None and value is not None:
#             if instance.__store__ is not None:
#                 idx = self._idx(instance)
#                 instance.__store__._document.find_and_modify(
#                     query={'_id': idx, self.name: None},
#                     update={"$set": {self.name: value}},
#                     upsert=False
#                     )
#                 value = self._update(instance.__store__, idx)
#
#             self.write(instance, value)
#
#
# class IncreasingNumericSyncVariable(SyncVariable):
#     """
#     Variable that can be set once
#     """
#
#     def __set__(self, instance, value):
#         val = self.read(instance)
#
#         if self.fix_fnc:
#             if val is not None and self.fix_fnc(val):
#                 return val
#
#         if value > val:
#             if instance.__store__ is not None:
#                 idx = self._idx(instance)
#                 current = self._update(instance.__store__, idx)
#                 while value > current:
#                     instance.__store__._document.find_and_modify(
#                         query={'_id': idx, self.name: current},
#                         update={"$set": {self.name: value}},
#                         upsert=False
#                     )
#                     current = self._update(instance.__store__, idx)
#
#                 value = current
#
#             self.write(instance, value)


class ObjectSyncVariable(SyncVariable):
    def __init__(self, name, store, fix_fnc=None):
        super(ObjectSyncVariable, self).__init__(name, fix_fnc)
        self.store = store

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            if self.fix_fnc:
                val = self.read(instance)
                if val is not None and self.fix_fnc(val):
                    return val

            if instance.__store__ is not None:
                idx = self._idx(instance)
                dct = self._update(instance.__store__, idx)

                if dct and self.name in dct:
                    data = dct[self.name]

                    if data is None:
                        value = None
                    else:
                        obj_idx = long(data['_hex_uuid'], 16)
                        value = getattr(instance.__store__.storage, self.store).load(obj_idx)

                    self.write(instance, value)
                    return value

            return self.read(instance)

    def __set__(self, instance, value):
        if instance.__store__ is not None:
            if self.fix_fnc:
                val = self.read(instance)
                if val is not None and self.fix_fnc(val):
                    return

            idx = self._idx(instance)
            if value is not None:
                instance.__store__._document.find_and_modify(
                    query={'_id': idx},
                    update={"$set": {self.name: {
                        '_hex_uuid': self._hex(value),
                        '_store': self.store}}},
                    upsert=False
                    )
            else:
                instance.__store__._document.find_and_modify(
                    query={'_id': idx},
                    update={"$set": {self.name: None}},
                    upsert=False
                    )

        self.write(instance, value)


_json_sync_simplifier = ObjectJSON()


class JSONDataSyncVariable(SyncVariable):
    def __init__(self, name, fix_fnc=None):
        super(JSONDataSyncVariable, self).__init__(name, fix_fnc)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            if self.fix_fnc:
                val = self.read(instance)
                if val is not None and self.fix_fnc(val):
                    return val

            if instance.__store__ is not None:
                idx = self._idx(instance)
                dct = self._update(instance.__store__, idx)

                if dct and self.name in dct:
                    data = dct[self.name]

                    if data is None:
                        value = None
                    else:
                        value = _json_sync_simplifier.build(data)

                    self.write(instance, value)
                    return value

            return self.read(instance)

    def __set__(self, instance, value):
        if instance.__store__ is not None:
            if self.fix_fnc:
                val = self.read(instance)
                if val is not None and self.fix_fnc(val):
                    return

            idx = self._idx(instance)
            if value is not None:
                instance.__store__._document.find_and_modify(
                    query={'_id': idx},
                    update={"$set": {self.name: _json_sync_simplifier.simplify(value)}},
                    upsert=False
                    )
            else:
                instance.__store__._document.find_and_modify(
                    query={'_id': idx},
                    update={"$set": {self.name: None}},
                    upsert=False
                    )

        self.write(instance, value)
