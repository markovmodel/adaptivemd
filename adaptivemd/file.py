from __future__ import print_function, absolute_import

import os
import time

from .mongodb import (StorableMixin, ObjectJSON,
                      JSONDataSyncVariable, SyncVariable, ObjectSyncVariable, DataDict)


class Location(StorableMixin):
    """
    A representation of a path in adaptiveMD

    This is an important part of adaptiveMD. It allows you to specify file
    paths also relative to certain special folders in adaptiveMD, like the
    project folder. These special paths will be interpreted by the schedulers
    when they actually execute tasks

    Note that folder names ALWAYS end in ``/`` while filenames NEVER

    You can use special prefixes

    - ``file://{relative}/{path}`` references local files. If you want
      absolute paths you start with ``file:///{absolute}/{path}``
    - ``worker://{relative_to_worker}`` relative to the working directory
    - ``staging://`` relative to staging directory
    - ``sandbox://`` relative to the sandbox, the folder that contains worker
      directories
    - ``shared://`` relative to the main shared FS folder
    - ``project://`` relative to the specific project folder. Usually in
      ``shared://projects/{project-name}/``

    Attributes
    ----------
    location : str
        the full location using special prefixed

    """
    allowed_drives = ['worker', 'staging', 'file', 'shared']
    default_drive = 'worker'

    use_absolute_local_paths = True

    _restore_non_initial_attr = False

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
            if self.drive == 'file' and not self.path.startswith('/'):
                p = os.path.abspath(self.path)
                self.location = 'file://' + p

    def clone(self):
        """
        Make a deep copy of the objects

        Returns
        -------
        `Location`
            the deep copy

        """
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
        """
        Returns
        -------
        bool
            True when the location is a temporary folder that might be
            deleted

        """
        return self.drive == 'worker'

    @property
    def short(self):
        """
        Returns
        -------
        str
            a shortened form of the path
        """
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
        """
        Returns
        -------
        str
            return the full form always with a prefix
        """
        return '%s://%s' % (self.drive, self.path)

    @property
    def basename(self):
        """
        Returns
        -------
        str
            the file basename

        """
        return os.path.basename(self.path)

    @property
    def is_folder(self):
        """
        Returns
        -------
        bool
            True if location is a folder
        """
        return not self.basename

    @property
    def path(self):
        """

        Returns
        -------
        str
            the complete path without prefix

        """
        return self.split_drive[1]

    @property
    def split(self):
        """
        Returns
        -------
            os.path.split on the :py:attr:`path` without prefixes
        """
        return os.path.split(self.path)

    @property
    def dirname(self):
        """

        Returns
        -------
        str
            the path of the directory, like os.path.dirname
        """
        return os.path.dirname(self.path)

    @property
    def drive(self):
        """
        return the prefix name

        Returns
        -------
        str
            the prefix name like `staging`, `project`, `worker`, file`

        """
        return self.split_drive[0]

    @property
    def extension(self):
        """

        Returns
        -------
        str
            the filename extension or '' of non exists

        """
        name = self.basename
        parts = name.split('.')
        if len(parts) == 1:
            return ''
        else:
            return parts[-1]

    @property
    def basename_short(self):
        """

        Returns
        -------
        str
            the basename without extension

        """
        name = self.basename
        parts = name.split('.')
        if len(parts) == 1:
            return name
        else:
            return '.'.join(parts[:-1])

    @property
    def split_drive(self):
        """

        Returns
        -------
        str
            the drive (prefix with ://)
        str
            the full path without prefix
        """
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
    """
    Represents a file object at a specific location

    `File` objects can but do not have to exist - you can check using the
    :py:attr:`File.created` attribute. If it is a positive number it represents
    the time stamp when it was created.
    """
    _find_by = ['created', 'task']

    created = SyncVariable('created', lambda x: x is not None and x < 0)
    _file = ObjectSyncVariable('_file', lambda x: x is not None)
    task = SyncVariable('task', lambda x: x is not None)

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
        """
        create a cloned object with equal attributes

        Returns
        -------
        `Location`
            the same type as this object
        """
        f = self.__class__(self.location)
        f.resource = self.resource
        f.created = None

        return f

    def create(self, scheduler):
        """
        Mark file as being existent on a specific scheduler.

        This should only work for file in ``staging://``, ``shared://``,
        ``sandbox://`` or ``file://``
        Files in ``worker://`` will potentially be deleted,
        others are already existing

        Notes
        -----
        We usually assume that objects are immutable. The way to think about
        creation is that a file is something like a *Promise* and it promises
        a certain file with a name. Once it is created it is still the same
        file but now it exists and can be used.

        The change of location is also a re-expression of the same location so
        that it is reusable.

        """
        scheduler.unroll_staging_path(self)
        self.created = time.time()

    def modified(self):
        """
        Mark a file as being altered and not existent anymore

        Notes
        -----
        Negative timestamps indicate the (negative) time when the object
        disappeared in the form described

        """
        stamp = self.created
        if stamp is not None and stamp > 0:
            self.created = - time.time()

    @property
    def exists(self):
        """

        Returns
        -------
        bool
            True if the file exists, i.e. has a positive `created` timestamp

        """
        created = self.created
        return created is not None and created > 0

    def _complete_target(self, target, extension=False):
        if target is None:
            target = Location('')

        if isinstance(target, str):
            target = Location(target)

        if isinstance(target, Location):
            if target.basename == '':
                target.location += self.basename

            if extension:
                target.location = target.location + '.' + self.extension

        return target

    def copy(self, target=None):
        """
        copy file to a target
        
        Shortcut for ``Copy(self, target)``

        Parameters
        ----------
        target : `Location` or str
            the target location

        Returns
        -------
        `adaptivemd.FileTransaction`
            the copy action

        """
        target = self._complete_target(target)
        return Copy(self, target)

    def move(self, target=None):
        """
        move file to a target

        Shortcut for ``Move(self, target)``

        Parameters
        ----------
        target : `Location` or str
            the target location

        Returns
        -------
        `adaptivemd.FileTransaction`
            the move action

        """
        target = self._complete_target(target)
        return Move(self, target)

    def link(self, target=None):
        """
        link file to a target

        Shortcut for ``Link(self, target)``

        Parameters
        ----------
        target : `Location` or str
            the target location

        Returns
        -------
        `adaptivemd.FileTransaction`
            the link action

        """
        target = self._complete_target(target)
        return Link(self, target)

    def transfer(self, target=None):
        """
        transfer file to a target

        Shortcut for `Transfer(self, target)`

        Parameters
        ----------
        target : `Location` or str
            the target location

        Returns
        -------
        `adaptivemd.FileTransaction`
            the transfer action

        """
        target = self._complete_target(target)
        return Transfer(self, target)

    def remove(self):
        """
        remove file

        Shortcut for `Remove(self)`

        Returns
        -------
        `adaptivemd.FileAction`
            the remove action

        """
        return Remove(self)

    def touch(self):
        """
        touch file

        Shortcut for `Touch(self)`

        Returns
        -------
        `adaptivemd.FileAction`
            the touch action

        """
        return Touch(self)

    def __repr__(self):
        return "'%s'" % self.basename

    def load(self, scheduler=None):
        """
        Load a local file into memory

        If you later store the file its content will be stored as well

        Parameters
        ----------
        scheduler : `Scheduler` or None
            if specifiied the scheduler can alter the filelocation with its
            usual rules. Normally you should not have to use it

        Returns
        -------
        self

        """
        if self.drive == 'file':
            if scheduler is not None:
                path = scheduler.replace_prefix(self.url)
            else:
                path = self.path

            with open(path, 'r') as f:
                self._file = DataDict(f.read())

        return self

    def to_dict(self):
        ret = super(File, self).to_dict()
        ret['_file'] = self._file
        # if self._file:
        #     ret['_file_'] = base64.b64encode(self._file)

        return ret

    @classmethod
    def from_dict(cls, dct):
        obj = super(File, cls).from_dict(dct)
        obj._file = dct['_file']
        return obj

    def get_file(self):
        """
        Return the file content it has been loaded

        Returns
        -------
        str or None
            the file content, if it exists None else
        """
        f = self._file
        if f:
            return self._file.data
        else:
            return None

    @property
    def has_file(self):
        """

        Returns
        -------
        bool
            True if the file content is attached.

        """
        return self._file is not None

    def set_file(self, content):
        """
        Set the file content.

        Can only be set once!

        Parameters
        ----------
        content : str
            the content of the file

        """
        self._file = DataDict(content)


_json_file_simplifier = ObjectJSON()


class JSONFile(File):
    """
    A special file which as assumed JSON readable content
    """
    _find_by = ['created', '_data', 'task']

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
        """

        Returns
        -------
        dict
            the parsed JSON content

        """
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
        if self._data is None:
            s = self.get(scheduler)
            if s is not None:
                self._data = s

        return self

    def get(self, scheduler=None):
        """
        Read data from the JSON file at the files location without storing

        Parameters
        ----------
        scheduler : `Scheduler` or None
            if given use the prefixing from the scheduler

        Returns
        -------
        dict
            the data in the file

        """
        if self._data is not None:
            return self._data

        path = None

        if self.drive == 'file':
            path = self.path

        if scheduler is not None:
            path = scheduler.get_path(self)

        if path:
            with open(path, 'r') as f:
                return _json_file_simplifier.from_json(f.read())

        return None

    @property
    def exists(self):
        if self.data is not None:
            return True

        created = self.created

        if created is not None and created > 0:
            return True

        return False


class Directory(File):
    """
    A directory

    Gets an additional ``/`` if missing at the end of the file location

    """
    def __init__(self, location):
        super(Directory, self).__init__(location)
        if not self.is_folder:
            self.location = os.path.join(self.location, '')


class URLGenerator(object):
    """
    A pathname generator

    Helps you to generate unique filenames.

    Examples
    --------
    >>> gen = URLGenerator('mypath/{count:04}.dcd')
    >>> next(gen)
    'mypath/0000.dcd'
    >>> next(gen)
    'mypath/0001.dcd'

    """
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

    __next__ = next

    def initialize_from_files(self, files):
        """
        Set the next available number from a list of files

        Parameters
        ----------
        files : list of `Location`

        """
        # a little cheat to figure out the last number

        # todo: might be better to store the current number in the project DB
        self.count = 0
        left = len(self.shape.split('{')[0].split('/')[-1])
        right = len(self.shape.split('}')[-1])
        for f in files:
            try:
                g = int(f.path[:-right].split('/')[-1][left:]) + 1
                self.count = max(g, self.count)
            except Exception:
                pass


##############################################################################
# Actions
##############################################################################

class Action(StorableMixin):
    """
    A bash-command-like action to be executed in a Task

    The main purpose is to have a worker/hpc independent description of
    what should happen. This objects carry all the necessary information
    and will be parsed into a bash script on the actual HPC / worker

    """
    def __init__(self):
        super(Action, self).__init__()

    def __repr__(self):
        return str(self)


class AddPathAction(Action):
    """
    An Action to add a path to the $PATH environment variables

    """
    def __init__(self, path):
        """
        Parameters
        ----------
        path : `Location` or str
            the path to be added

        """
        super(AddPathAction, self).__init__()
        self.path = path


class FileAction(Action):
    """
    An Action that involves (at least) one file called source

    Attributes
    ----------
    source : `File`
        the source file for the action

    """
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
        """
        Returns
        -------
        list of `File`
            the necessary list of files to be functional

        """
        return [self.source]

    @property
    def added(self):
        """
        Returns
        -------
        list of `File`
            the list of files added to the project by this action

        """
        return []

    @property
    def removed(self):
        """
        Returns
        -------
        list of `File`
            the list of files removed by this action

        """
        return []


class Touch(FileAction):
    """
    An action that creates an empty file or folder

    """
    pass


class MakeDir(FileAction):
    """
    An action that creates a folder

    """
    pass


class FileTransaction(FileAction):
    """
    An action involving a source and a target file

    Attributes
    ----------
    target : `File`
        the target file

    """
    def __init__(self, source, target):
        """

        Parameters
        ----------
        source : `File`
            the source file for the action
        target : `File` or `Location` or str
            the target location for the action

        """
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


class Copy(FileTransaction):
    """
    An action that copies a file from source to target

    """
    pass


class Transfer(FileTransaction):
    """
    An action that transfers between local and HPC

    """
    pass


class Link(FileTransaction):
    """
    An action that links a source file to a target

    """
    pass


class Move(FileTransaction):
    """
    An action that moves a file from source to target

    The source is removed in the process

    """
    @property
    def removed(self):
        return [self.source]


class Remove(FileAction):
    """
    An action that removes a file

    """
    @property
    def removed(self):
        return [self.source]

    @property
    def added(self):
        return []
