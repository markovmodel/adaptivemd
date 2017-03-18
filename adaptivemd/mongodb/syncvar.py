import uuid
import weakref

from dictify import ObjectJSON


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
                val = self.values.get(instance)
                if val is not None and self.fix_fnc(val):
                    return val

            if instance.__store__ is not None:
                idx = self._idx(instance)
                value = self._update(instance.__store__, idx)
                self.values[instance] = value
                return value
            else:
                return self.values.get(instance)

    def __set__(self, instance, value):
        if instance.__store__ is not None:
            if self.fix_fnc:
                val = self.values.get(instance)
                if val is not None and self.fix_fnc(val):
                    return

            idx = str(uuid.UUID(int=instance.__uuid__))
            instance.__store__._document.find_and_modify(
                query={'_id': idx},
                update={"$set": {self.name: value}},
                upsert=False
                )

        self.values[instance] = value


class NoneOrValueSyncVariable(SyncVariable):
    """
    Variable that can be set once
    """

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            if self.values.get(instance) is None:
                idx = self._idx(instance)
                value = self._update(instance.__store__, idx)
                self.values[instance] = value
                return value

            return self.values.get(instance)

    def __set__(self, instance, value):
        if self.values.get(instance) is None and value is not None:
            if instance.__store__ is not None:
                idx = self._idx(instance)
                instance.__store__._document.find_and_modify(
                    query={'_id': idx, self.name: None},
                    update={"$set": {self.name: value}},
                    upsert=False
                    )
                value = self._update(instance.__store__, idx)

            self.values[instance] = value


class IncreasingNumericSyncVariable(SyncVariable):
    """
    Variable that can be set once
    """

    def __set__(self, instance, value):
        val = self.values.get(instance)

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

            self.values[instance] = value


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
                val = self.values.get(instance)
                if val is not None and self.fix_fnc(val):
                    return

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

        self.values[instance] = value


_json_sync_simplifier = ObjectJSON()


class JSONDataSyncVariable(SyncVariable):
    def __init__(self, name, fix_fnc=None):
        super(JSONDataSyncVariable, self).__init__(name, fix_fnc)

    def _update(self, store, idx):
        if store is not None:
            data = store._document.find_one(
                {'_id': idx})[self.name]
            if data is None:
                return None
            else:
                return _json_sync_simplifier.build(data)

    def __set__(self, instance, value):
        if instance.__store__ is not None:
            if self.fix_fnc:
                val = self.values.get(instance)
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

        self.values[instance] = value