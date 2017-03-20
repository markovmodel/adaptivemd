import os
import time
import base64

from mongodb import StorableMixin, ObjectJSON, \
    JSONDataSyncVariable, SyncVariable


class Action(StorableMixin):
    def __init__(self):
        super(Action, self).__init__()

    def __repr__(self):
        return str(self)


class AddPathAction(Action):
    def __init__(self, path):
        super(AddPathAction, self).__init__()
        self.path = path


class FileAction(Action):
    def __init__(self, source):
        super(FileAction, self).__init__()
        self.source = source

    def __str__(self):
        return "%s('%s')" % (
            self.__class__.__name__,
            self.source
        )

    @property
    def required(self):
        return [self.source]

    @property
    def added(self):
        return []

    @property
    def removed(self):
        return []


class FileTransaction(FileAction):
    def __init__(self, source, target):
        super(FileTransaction, self).__init__(source)

        if isinstance(target, str):
            self.target = source.clone()
            self.target.location = target
        elif isinstance(target, Location) and not isinstance(target, File):
            self.target = source.clone()
            self.target.location = target.location
        else:  # e.g. when it is already a `File` object
            self.target = target

    def __str__(self):
        return "%s('%s' > '%s)" % (
            self.__class__.__name__,
            self.source.short,
            self.target.short
        )

    @property
    def added(self):
        return [self.target]


class Touch(FileAction):
    pass


class MakeDir(FileAction):
    pass


class Copy(FileTransaction):
    pass


class Transfer(FileTransaction):
    pass


class Link(FileTransaction):
    pass


class Move(FileTransaction):
    @property
    def removed(self):
        return [self.source]



class Remove(FileAction):
    @property
    def removed(self):
        return [self.source]

    @property
    def added(self):
        return []


class Location(StorableMixin):
    allowed_drives = ['worker', 'staging', 'file', 'shared']
    default_drive = 'worker'

    use_absolute_local_paths = True

    _ignore = True

    def __init__(self, location):
        super(Location, self).__init__()

        if isinstance(location, Location):
            self.location = location.location
        elif isinstance(location, str):
            self.location = location
        else:
            raise ValueError('location can only be a `File` or a string.')

        # fix relative paths for file://

        if File.use_absolute_local_paths:
            if self.drive == 'file':

                p = os.path.abspath(self.path)
                self.location = 'file://' + p

    def clone(self):
        return self.__class__(self.location)

    def __add__(self, other):
        if isinstance(other, str):
            return str(self) + other

        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            return other + str(self)

    @property
    def is_temp(self):
        return self.drive == 'worker'

    @property
    def short(self):
        if self.path == self.basename:
            return '%s://%s' % (self.drive, self.basename)
        elif self.path == '/' + self.basename:
            return '%s:///%s' % (self.drive, self.basename)
        elif self.is_folder:
            s = self.dirname.split('/')
            if len(s) == 1:
                return '%s://%s/' % (self.drive, s[-1])
            elif s[0] == '':
                if len(s) == 2:
                    return '%s:///%s/' % (self.drive, s[-1])
                else:
                    return '%s:///{}/%s/' % (self.drive, s[-1])
            else:
                return '%s://{}/%s/' % (self.drive, s[-1])
        else:
            return '%s://{}/%s' % (self.drive, self.basename)

    @property
    def url(self):
        return '%s://%s' % (self.drive, self.path)

    @property
    def basename(self):
        return os.path.basename(self.path)

    @property
    def resource_location(self):
        return self.location

    @property
    def is_folder(self):
        return not self.basename

    @property
    def path(self):
        return self.split_drive[1]

    @property
    def split(self):
        return os.path.split(self.path)

    @property
    def dirname(self):
        return os.path.dirname(self.path)

    @property
    def drive(self):
        return self.split_drive[0]

    @property
    def extension(self):
        name = self.basename
        parts = name.split('.')
        if len(parts) == 1:
            return ''
        else:
            return parts[-1]

    @property
    def basename_short(self):
        name = self.basename
        parts = name.split('.')
        if len(parts) == 1:
            return name
        else:
            return '.'.join(parts[:-1])

    @property
    def split_drive(self):
        s = self.location
        parts = s.split('://')
        if len(parts) == 2:
            return parts[0], parts[1]
        elif len(parts) == 1:
            return self.default_drive, parts[0]

    def __repr__(self):
        return "'%s'" % self.location

    def __str__(self):
        # return the full location so we can later parse it accordingly
        return self.url


class File(Location):
    _find_by = ['created', 'state', '_file', 'task']

    created = SyncVariable('created', lambda x: x is not None and x < 0)
    _file = SyncVariable('_file', lambda x: not bool(x))
    task = SyncVariable('task', lambda x: not bool(x))

    def __init__(self, location):
        super(File, self).__init__(location)

        self.resource = None
        self.created = None
        self._file = None
        self.task = None

        if self.drive == 'file':
            if os.path.exists(self.path):
                self.created = time.time()

    @property
    def _ignore(self):
        return self.drive == 'worker' or self.drive == 'staging'

    @property
    def generator(self):
        if self.task:
            return self.task.generator

        return None

    def clone(self):
        f = self.__class__(self.location)
        f.resource = self.resource
        f.created = None

        return f

    def create(self, scheduler):
        """
        Mark file as being existent on a specific scheduler.

        This should only work for file in `staging://`, `shared://`,
        `sandbox://` or `file://`
        Files in `unit://` will potentially be deleted, others are already existing

        Notes
        -----
        We usually assume that objects are immutable. The way to think about
        creation is that a file is something like a _Promise_ and it promises
        a certain file with a name. Once it is created it is still the same file
        but now it exists and can be used.

        The change of location is also a re-expression of the same location so
        that it is reusable.

        """
        scheduler.unroll_staging_path(self)
        self.created = time.time()

    def modified(self):
        """
        Mark a file as being altered and hence not existent anymore in the current description

        Notes
        -----
        Negative timestamps indicate the (negative) time when the object disappeared
        in the form described
        """
        stamp = self.created
        if stamp is not None and stamp > 0:
            self.created = - time.time()

    @property
    def exists(self):
        created = self.created
        return created is not None and created > 0

    def _complete_target(self, target, extension=False):
        if target is None:
            target = Location('')

        if isinstance(target, str):
            target = Location(target)

        if isinstance(target, Location):
            if target.basename == '':
                target.location = target.location + self.basename

            if extension:
                target.location = target.location + '.' + self.extension

        return target

    def copy(self, target=None):
        target = self._complete_target(target)
        return Copy(self, target)

    def move(self, target=None):
        target = self._complete_target(target)
        return Move(self, target)

    def link(self, target=None):
        target = self._complete_target(target)
        return Link(self, target)

    def transfer(self, target=None):
        target = self._complete_target(target)
        return Transfer(self, target)

    def remove(self):
        return Remove(self)

    def touch(self):
        return Touch(self)

    def __repr__(self):
        return "'%s'" % self.basename

    def load(self, scheduler=None):
        if self.drive == 'file':
            if scheduler is not None:
                path = scheduler.replace_prefix(self.url)
            else:
                path = self.path

            with open(path, 'r') as f:
                self._file = f.read()

        return self

    def to_dict(self):
        ret = super(File, self).to_dict()
        if self._file:
            ret['_file_'] = base64.b64encode(self._file)

        return ret

    @classmethod
    def from_dict(cls, dct):
        obj = super(File, cls).from_dict(dct)
        if '_file_' in dct:
            obj._file = base64.b64decode(dct['_file_'])

        return obj

    def get_file(self):
        return self._file

    @property
    def has_file(self):
        return bool(self._file)

    def set_file(self, content):
        self._file = content


_json_file_simplifier = ObjectJSON()


class JSONFile(File):
    _find_by = ['created', 'state', '_data']

    _data = JSONDataSyncVariable('_data', lambda x: not None)
    # _file = SyncVariable('_data', lambda x: not None)
    _file = None
    # _data = ObjectSyncVariable('_data', 'data', lambda x: not None)

    def __init__(self, location):
        super(JSONFile, self).__init__(location)
        self._data = None

    def to_dict(self):
        ret = super(File, self).to_dict()
        ret['_data'] = self._data

        return ret

    @classmethod
    def from_dict(cls, dct):
        obj = super(File, cls).from_dict(dct)
        obj._data = dct['_data']
        return obj

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def has_file(self):
        return self._data is not None

    def get_file(self):
        if self._data is not None:
            return _json_file_simplifier.to_json(self._data)

        return None

    def load(self, scheduler=None):
        path = None

        if self.drive == 'file':
            path = self.path

        if scheduler is not None:
            path = scheduler.get_path(self)

        if path:
            with open(path, 'r') as f:
                self._data = _json_file_simplifier.from_json(f.read())

        return self

    @property
    def exists(self):
        if self.data is not None:
            return True

        created = self.created

        if created is not None and created > 0:
            return True

        return False


# class MultiFile(File):
#
#     _file_attributes = []
#
#     def __init__(self, location):
#         super(MultiFile, self).__init__(location)
#
#     def _multi_action(self, cls, target=None):
#         if self._file_attributes:
#             target = self._complete_target(target)
#             ret = [cls(self, target)]
#             for attr in self._file_attributes:
#                 f = getattr(self, attr)
#                 target = f._complete_target(target, True)
#                 ret += [cls(f, target)]
#
#         else:
#             target = self._complete_target(target)
#             ret = cls(self, target)
#
#         return ret
#
#     def copy(self, target=None):
#         return self._multi_action(Copy, target)
#
#     def move(self, target=None):
#         return self._multi_action(Move, target)
#
#     def link(self, target=None):
#         return self._multi_action(Link, target)
#
#     def transfer(self, target=None):
#         return self._multi_action(Transfer, target)
#
#     def remove(self):
#         if self._file_attributes:
#             ret = [Remove(self)]
#             for ext, attr in self._file_attributes.items():
#                 f = getattr(self, attr)
#                 ret += [Remove(f)]
#         else:
#             ret = Remove(self)
#
#         return ret


class Directory(File):
    def __init__(self, location):
        super(Directory, self).__init__(location)
        if not self.is_folder:
            self.location = os.path.join(self.location, '')


class URLGenerator(object):
    def __init__(self, shape, bundle=None):
        if bundle is None:
            self.count = 0
        else:
            self.count = len(bundle)

        self.shape = shape

    def __iter__(self):
        return self

    def next(self):
        fn = self.shape.format(count=self.count)
        self.count += 1
        return fn

    def initialize_from_files(self, files):
        # a little cheat to figure out the last number
        self.count = 0
        left = len(self.shape.split('{')[0].split('/')[-1])
        right = len(self.shape.split('}')[-1])
        for f in files:
            try:
                g = int(f.path[:-right].split('/')[-1][left:]) + 1
                self.count = max(g, self.count)
            except Exception:
                pass
