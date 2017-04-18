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


import base64
import importlib

import numpy as np
import math
import abc
from uuid import UUID

import ujson

import marshal
import types
import opcode
import __builtin__

from base import StorableMixin

__author__ = 'Jan-Hendrik Prinz'


class ObjectJSON(object):
    """
    A simple implementation of a pickle algorithm to create object that can be
    converted to json and back
    """

    allow_marshal = True

    # switch to `true`, if you want more protection
    prevent_unsafe_modules = False

    allowed_storable_atomic_types = [
        int, float, bool, long, str,
        np.float32, np.float64,
        np.int8, np.int16, np.int32, np.int64,
        np.uint8, np.uint16, np.uint32, np.uint64,
    ]

    safe_modules = [
        'numpy',
        'math',
        'pandas',
        'mdtraj',
        'simtk',
        'simtk.unit',
        'simtk.openmm'
    ]

    def __init__(self, unit_system=None):
        self.excluded_keys = []
        self.unit_system = unit_system
        self.class_list = dict()
        self.allowed_storable_types = dict()
        self.type_names = {}
        self.type_classes = {}

        self.update_class_list()

    def update_class_list(self):
        self.class_list = StorableMixin.objects()
        self.type_names = {
            cls.__name__: cls for cls in self.allowed_storable_atomic_types}
        self.type_names.update(self.class_list)
        self.type_classes = {
            cls: name for name, cls in self.type_names.iteritems()}

    def simplify_object(self, obj):
        return {
            '_cls': obj.__class__.__name__,
            '_dict': self.simplify(obj.to_dict(), obj.base_cls_name)
        }

    def simplify(self, obj, base_type=''):
        if obj.__class__.__name__ == 'module':
            # store an imported module
            if obj.__name__.split('.')[0] in self.safe_modules:
                return {'_import': obj.__name__}
            else:
                raise RuntimeError((
                    'The module reference "%s" you want to store is '
                    'not allowed!') % obj.__name__)

        elif type(obj) is type or type(obj) is abc.ABCMeta:
            # store a storable number type
            if obj in self.type_classes:
                return {'_type': obj.__name__}
            else:
                return None

        elif type(obj) is float and math.isinf(obj):
            return {
                '_float': str(obj)}

        elif type(obj) is int and math.isinf(obj):
            return {
                '_integer': str(obj)}

        elif obj.__class__.__module__ != '__builtin__':
            # if obj.__class__ is units.Quantity:
            #     # This is number with a unit so turn it into a list
            #     if self.unit_system is not None:
            #         return {
            #             '_value': self.simplify(
            #                 obj.value_in_unit_system(self.unit_system)),
            #             '_units': self.unit_to_dict(
            #                 obj.unit.in_unit_system(self.unit_system))
            #         }
            #     else:
            #         return {
            #             '_value': self.simplify(obj / obj.unit, base_type),
            #             '_units': self.unit_to_dict(obj.unit)
            #         }
            if obj.__class__ is np.ndarray:
                # this is maybe not the best way to store large numpy arrays!
                return {
                    '_numpy': self.simplify(obj.shape),
                    '_dtype': str(obj.dtype),
                    '_data': base64.b64encode(obj.copy(order='C'))
                }
            elif hasattr(obj, 'to_dict'):
                # the object knows how to dismantle itself into a json string
                if hasattr(obj, '__uuid__'):
                    return {
                        '_cls': obj.__class__.__name__,
                        '_obj_uuid': str(UUID(int=obj.__uuid__)),
                        '_dict': self.simplify(obj.to_dict(), base_type)}
                else:
                    return {
                        '_cls': obj.__class__.__name__,
                        '_dict': self.simplify(obj.to_dict(), base_type)}
            elif type(obj) is UUID:
                return {
                    '_uuid': str(UUID(int=obj))}

            # we will convert numpy scalars to python scalar (and cross fingers)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.int_):
                return int(obj)
            elif isinstance(obj, np.float_):
                # todo: this might be dangerous - potential loss of accuracy
                return float(obj)
            else:
                return None
        elif type(obj) is list:
            return [self.simplify(o, base_type) for o in obj]
        elif type(obj) is tuple:
            return {'_tuple': [self.simplify(o, base_type) for o in obj]}
        elif type(obj) is dict:
            # we want to support storable objects as keys so we need to wrap
            # dicts with care and store them using tuples

            simple = [
                key for key in obj.keys()
                if type(key) is str or type(key) is int]

            if len(simple) < len(obj):
                # other keys than int or str
                result = {
                    '_dict': [
                        self.simplify(tuple([key, o]))
                        for key, o in obj.iteritems()
                        if key not in self.excluded_keys
                    ]}
            else:
                result = {
                    key: self.simplify(o) for key, o in obj.iteritems()
                    if key not in self.excluded_keys
                }

            return result
        elif type(obj) is slice:
            return {
                '_slice': [obj.start, obj.stop, obj.step]}
        else:
            oo = obj
            return oo

    @staticmethod
    def _unicode2str(s):
        if type(s) is unicode:
            return s.encode('utf8')
        else:
            return s

    def build(self, obj):
        if type(obj) is dict:
            # if '_units' in obj and '_value' in obj:
            #     return self.build(
            #         obj['_value']) * self.unit_from_dict(obj['_units'])

            if '_slice' in obj:
                return slice(*obj['_slice'])

            elif '_numpy' in obj:
                return np.frombuffer(
                    base64.decodestring(obj['_data']),
                    dtype=np.dtype(obj['_dtype'])).reshape(
                        self.build(obj['_numpy'])
                )

            elif '_float' in obj:
                return float(str(obj['_float']))

            elif '_integer' in obj:
                return float(str(obj['_integer']))

            elif '_uuid' in obj:
                return int(UUID(obj['_uuid']))

            elif '_cls' in obj and '_dict' in obj:
                if obj['_cls'] not in self.class_list:
                    self.update_class_list()
                    if obj['_cls'] not in self.class_list:
                        # updating did not help, so there is nothing we can do.
                        raise ValueError((
                            'Cannot create obj of class `%s`.\n' +
                            'Class is not registered as creatable! '
                            'You might have to define\n' +
                            'the class locally and call '
                            '`update_storable_classes()` on your storage.') %
                            obj['_cls'])

                attributes = self.build(obj['_dict'])
                ret = self.class_list[obj['_cls']].from_dict(attributes)
                if '_obj_uuid' in obj:
                    # vals = {x: getattr(ret, x) for x in ret._find_by}
                    ret.__uuid__ = int(UUID(obj['_obj_uuid']))
                    # for k,v in vals.iteritems():
                    #     setattr(ret, )

                return ret

            elif '_tuple' in obj:
                return tuple([self.build(o) for o in obj['_tuple']])

            elif '_type' in obj:
                # return a type of a _built-in_ `storable` type
                return self.type_names.get(obj['_type'])

            elif '_dict' in obj:
                return {
                    self._unicode2str(self.build(key)): self.build(o)
                    for key, o in self.build(obj['_dict'])
                }

            elif '_import' in obj:
                module = obj['_import']
                if module.split('.')[0] in self.safe_modules:
                    imp = importlib.import_module(module)
                    return imp
                else:
                    return None

            elif '_marshal' in obj or '_module' in obj:
                return self.callable_from_dict(obj)

            else:
                return {
                    self._unicode2str(key): self.build(o)
                    for key, o in obj.iteritems()
                }

        elif type(obj) is list:
            return [self.build(o) for o in obj]

        elif type(obj) is unicode:
            return self._unicode2str(obj)

        else:
            return obj

    @staticmethod
    def unit_to_symbol(unit):
        return str(1.0 * unit).split()[1]

    # @staticmethod
    # def unit_to_dict(unit):
    #     unit_dict = {
    #         p.name: int(fac) for p, fac in unit.iter_base_or_scaled_units()}
    #     return unit_dict
    #
    # @staticmethod
    # def unit_from_dict(unit_dict):
    #     unit = units.Unit({})
    #     for unit_name, unit_multiplication in unit_dict.iteritems():
    #         unit *= getattr(units, unit_name) ** unit_multiplication
    #
    #     return unit

    @staticmethod
    def callable_to_dict(c):
        """
        Turn a callable function of class into a dictionary

        Used for conversion to JSON

        Parameters
        ----------
        c : callable (function or class with __call__)
            the function to be turned into a dict representation

        Returns
        -------
        dict
            the dict representation of the callable
        """
        f_module = c.__module__
        root_module = f_module.split('.')[0]

        # is_class = isinstance(c, (type, types.ClassType))

        # try saving known external classes of functions, e.g. `msmbuilder`
        if root_module in ObjectJSON.safe_modules:
            # only store the function/class and the module
            return {
                '_module': c.__module__,
                '_name': c.__name__
            }

        # if the easy way did not work, try saving it using bytecode
        if ObjectJSON.allow_marshal and callable(c):
            # use marshal
            global_vars = ObjectJSON._find_var(c, opcode.opmap['LOAD_GLOBAL'])
            import_vars = ObjectJSON._find_var(c, opcode.opmap['IMPORT_NAME'])

            builtins = dir(__builtin__)

            global_vars = list(set(
                [var for var in global_vars if var not in builtins]))
            import_vars = list(set(import_vars))

            err = ''

            if len(global_vars) > 0:
                err += 'The function you try to save relies on globally set ' \
                       'variables and these cannot be saved since storage ' \
                       'has no access to the global scope which includes ' \
                       'imports! \n\n'
                err += 'We require that the following globals: ' + \
                       str(global_vars) + ' either\n'
                err += '\n1. be replaced by constants'
                err += '\n2. be defined inside your function,' + \
                       '\n\n' + '\n'.join(
                           map(lambda x: ' ' * 8 + x + '= ...', global_vars)
                       ) + '\n'
                err += '\n3. imports need to be "re"-imported inside your ' \
                       'function' + \
                       '\n\n' + '\n'.join(
                           map(lambda x: ' ' * 8 + 'import ' + x, global_vars)
                       ) + '\n'
                err += '\n4. be passed as an external parameter ' \
                       '(not for imports!)'
                err += '\n\n        my_cv = FunctionCV("cv_name", ' + \
                       c.func_name + ', \n' + \
                       ',\n'.join(
                           map(lambda x: ' ' * 20 + x + '=' + x, global_vars)
                       ) + ')' + '\n'
                err += '\n    and change your function definition like this'
                err += '\n\n        def ' + \
                       c.func_name + '(snapshot, ...,  ' + \
                       '\n' + ',\n'.join(
                           map(lambda x: ' ' * 16 + x, global_vars)
                       ) + '):'

            unsafe_modules = [
                module for module in import_vars
                if module not in ObjectJSON.safe_modules
            ]

            if ObjectJSON.prevent_unsafe_modules and len(unsafe_modules) > 0:
                if len(err) > 0:
                    err += '\n\n'

                err += 'The function you try to save requires the following' \
                       ' modules to be installed: ' + str(unsafe_modules) + \
                       ' which are not marked as safe! '
                err += 'You can change the list of safe modules using '
                err += '\n\n        ObjectJSON.safe_modules.extend(['
                err += '\n' + ',\n'.join(
                       map(lambda x: ' ' * 12 + x, unsafe_modules)
                )
                err += '\n        ])'
                err += '\n\n'
                err += 'include the import statement in your function like'
                err += '\n\n' + '\n'.join(
                    [' ' * 8 + 'import ' + v for v in unsafe_modules])

            if len(err) > 0:
                raise RuntimeError('Cannot store function! \n\n' +
                                   word_wrap(err, 60))

            return {
                '_marshal': base64.b64encode(
                    marshal.dumps(c.func_code)),
                '_global_vars': global_vars,
                '_module_vars': import_vars
            }

        raise RuntimeError('Locally defined classes are not storable yet')

    @staticmethod
    def callable_from_dict(c_dict):
        """
        Turn a dictionary back in a callable function or class

        Used for conversion from JSON

        Parameters
        ----------
        c_dict : dict
            the dictionary that contains the information

        Returns
        -------
        callable
            the reconstructed callable function or class

        """
        c = None

        if c_dict is not None:
            if '_marshal' in c_dict:
                if ObjectJSON.allow_marshal:
                    code = marshal.loads(base64.b64decode(c_dict['_marshal']))
                    c = types.FunctionType(code, globals(), code.co_name)

            elif '_module' in c_dict:
                module = c_dict['_module']
                packages = module.split('.')
                if packages[0] in ObjectJSON.safe_modules:
                    imp = importlib.import_module(module)
                    c = getattr(imp, c_dict['_name'])

        return c

    @staticmethod
    def _find_var(code, op):
        """
        Helper function to search in python bytecode for specific function calls

        Parameters
        ----------
        code : function
            the python bytecode to be searched
        op : int
            the int code of the code to be found

        Returns
        -------
        list of func_code.co_names
            a list of co_names used in this function when calling op
        """

        # TODO: Clean this up. It now works only for codes that use co_names
        opcodes = code.func_code.co_code
        i = 0
        ret = []
        while i < len(opcodes):
            int_code = ord(opcodes[i])
            if int_code == op:
                ret.append((i, ord(opcodes[i + 1]) + ord(opcodes[i + 2]) * 256))

            if int_code < opcode.HAVE_ARGUMENT:
                i += 1
            else:
                i += 3

        return [code.func_code.co_names[i[1]] for i in ret]

    def to_json(self, obj, base_type=''):
        simplified = self.simplify(obj, base_type)
        return ujson.dumps(simplified)

    def to_json_object(self, obj):
        if hasattr(obj, 'base_cls') \
                and type(obj) is not type and type(obj) is not abc.ABCMeta:
            simplified = self.simplify_object(obj)
        else:
            simplified = self.simplify(obj)

        return ujson.dumps(simplified)

    def from_json(self, json_string):
        simplified = ujson.loads(json_string)
        return self.build(simplified)

    # def unit_to_json(self, unit):
    #     simple = self.unit_to_dict(unit)
    #     return self.to_json(simple)
    #
    # def unit_from_json(self, json_string):
    #     return self.unit_from_dict(self.from_json(json_string))

    def from_simple_dict(self, simplified):
        obj = self.build(simplified)

        obj.__uuid__ = int(UUID(simplified.get('_id')))
        obj.__time__ = simplified.get('_time', 0)  # use time or 0 if unset

        if 'name' in simplified:
            obj.name = simplified['name']

        for key in obj._find_by:
            if key in simplified:
                setattr(obj, key, self.build(simplified[key]))

        return obj

    def to_simple_dict(self, obj, base_type=''):
        dct = {
            '_cls': obj.__class__.__name__,
            '_obj_uuid': str(UUID(int=obj.__uuid__)),
            '_dict': self.simplify(obj.to_dict(), base_type),
            '_id': str(UUID(int=obj.__uuid__)),
            '_time': int(obj.__time__)}

        if hasattr(obj, 'name'):
            dct['name'] = obj.name

        for key in obj._find_by:
            if hasattr(obj, key):
                dct[key] = self.simplify(getattr(obj, key))

        return dct


class UUIDObjectJSON(ObjectJSON):
    def __init__(self, storage, unit_system=None):
        super(UUIDObjectJSON, self).__init__(unit_system)
        self.excluded_keys = ['json']
        self.storage = storage

    def simplify(self, obj, base_type=''):
        if obj is self.storage:
            return {'_storage': 'self'}

        if obj.__class__.__module__ != '__builtin__':
            if obj.__class__ in self.storage._obj_store:
                if not obj._ignore:
                    store = self.storage._obj_store[obj.__class__]
                    store.save(obj)
                    return {
                        '_hex_uuid': hex(obj.__uuid__),
                        '_store': store.name}

        return super(UUIDObjectJSON, self).simplify(obj, base_type)

    def build(self, obj):
        if type(obj) is dict:
            if '_storage' in obj:
                if obj['_storage'] == 'self':
                    return self.storage

            if '_obj_uuid' in obj and '_store' in obj:
                store = self.storage._stores[obj['_store']]
                result = store.load(int(UUID(obj['_obj_uuid'])))

                return result

            if '_hex_uuid' in obj and '_store' in obj:
                store = self.storage._stores[obj['_store']]
                result = store.load(long(obj['_hex_uuid'], 16))

                return result

        return super(UUIDObjectJSON, self).build(obj)


# a little code snippet to wrap strings around for nicer output
# idea found @ http://www.saltycrane.com/blog/2007/09/python-word-wrap-function/

def word_wrap(string, width=80):
    lines = string.split('\n')

    lines = [x.rstrip() for x in lines]
    result = []
    for line in lines:
        while len(line) > width:
            marker = width - 1
            while not line[marker].isspace():
                marker -= 1

            result.append(line[0:marker])
            line = line[marker + 1:]

        result.append(line)
    return '\n'.join(result)
