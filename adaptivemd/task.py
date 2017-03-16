import os
import uuid

from file import File
from util import get_function_source
from mongodb import StorableMixin, SyncVariable, ObjectSyncVariable


class BaseTask(StorableMixin):
    """
    Enhanced version of the ComputeUnitDescription

    This mainly makes it easier to create a CU for RP. Similar to the
    purpose of RP kernels.

    """

    _copy_attributes = [
        '_task_pre_stage', '_task_post_stage',
        '_pre_stage', '_pre_stage', '_post_stage',
        '_task_post_exec', '_task_pre_exec',
        '_user_pre_exec', '_user_post_exec',
        '_add_paths', '_environment'
        ]

    def __init__(self):
        super(BaseTask, self).__init__()

        self._task_pre_stage = []
        self._task_post_stage = []

        self._pre_stage = []
        self._post_stage = []

        self._task_post_exec = []
        self._task_pre_exec = []

        self._user_pre_exec = []
        self._user_post_exec = []

        self._add_paths = []
        self._environment = {}

    @staticmethod
    def _format_export_paths(paths):
        paths = sorted(list(set(paths)))
        return map('export PATH={}:$PATH'.format, paths)

    @staticmethod
    def _format_environment(env):
        if env:
            envs = [(key, env[key]) for key in sorted(list(env))]
            return ['export {0}={1}'.format(key, value) for key, value in envs]
        else:
            return []

    @property
    def pre_add_paths(self):
        return self._add_paths

    @property
    def environment(self):
        return self._environment

    @property
    def pre_exec_tail(self):
        return (
            self._task_pre_stage +
            self._task_pre_exec +
            self._pre_stage +
            self._user_pre_exec)

    @property
    def pre_exec(self):
        return (
            self._format_export_paths(self.pre_add_paths) +
            self._format_environment(self.environment) +
            self.pre_exec_tail)

    @property
    def post_exec(self):
        return (
            self._user_post_exec + self._post_stage +
            self._task_pre_exec + self._task_post_stage)

    @property
    def input_staging(self):
        return self._task_pre_stage + self._pre_stage

    @property
    def output_staging(self):
        return self._post_stage + self._task_post_stage

    def add_path(self, path):
        if isinstance(path, str):
            self._add_paths.append(path)
        elif isinstance(path, (list, tuple)):
            self._add_paths.extend(path)

    def __rshift__(self, other):
        if other is None:
            return self
        elif isinstance(other, Task):
            return EnclosedTask(self, other)


class Task(BaseTask):
    """
    A description for a task running on an HPC

    Attributes
    ----------
    worker : `WorkingScheduler`

    """
    _events = ['submit', 'fail', 'success', 'change']

    _copy_attributes = BaseTask._copy_attributes + [
        'executable', 'arguments',
        'cores', 'mpi', 'stdout',
        'stderr', 'kernel', 'name', 'restartable', 'cleanup',
        'generator', 'dependencies', 'state', 'worker'
        ]

    _find_by = ['state', 'worker', 'stderr', 'stdout']

    state = SyncVariable('state', lambda x: x in ['success', 'cancelled'])
    worker = ObjectSyncVariable('worker', 'workers')
    stdout = ObjectSyncVariable('stdout', 'logs', lambda x: x is not None)
    stderr = ObjectSyncVariable('stderr', 'logs', lambda x: x is not None)

    FINAL_STATES = ['success', 'cancelled']
    RESTARTABLE_STATES = ['fail', 'halted']
    RUNNABLE_STATES = ['created']

    def __init__(self, generator=None):
        super(Task, self).__init__()

        self.generator = generator
        self.dependencies = None
        self._on = {}
        self._add_files = []

        self.executable = None
        self.arguments = None

        self.cores = 1
        self.mpi = False

        self.stdout = None
        self.stderr = None

        self.kernel = None
        self.name = None

        self.restartable = None
        self.cleanup = None
        self.restart_failed = False

        self.add_cb('fail', self.__class__._default_fail)
        self.add_cb('success', self.__class__._default_success)

        self.state = 'created'

        self.worker = None

    def restart(self):
        """
        Mark a task as being runnable if it was stopped or failed before

        Returns
        -------

        """
        state = self.state
        if state in Task.RESTARTABLE_STATES:
            self.state = 'created'
            return True

        return False

    def cancel(self):
        """
        Mark a task as cancelled if it it not running or has been halted

        Returns
        -------

        """
        state = self.state
        if state in ['halted', 'created']:
            self.state = 'cancelled'
            return True

        return False

    @property
    def dependency_okay(self):
        dependencies = self.dependencies
        if dependencies is not None:
            return all(d.state == 'success' for d in self.dependencies)

        return True

    @property
    def ready(self):
        if self.dependencies:
            return self.dependency_okay

        return True

    def add_conda_env(self, name):
        """
        Add loading a conda env to all tasks of this resource

        This calls `resource.wrapper.pre_bash('source activate {name}')`
        Parameters
        ----------
        name : str
            name of the conda environment

        """
        self.pre_bash('source activate %s' % name)

    def _default_fail(self, scheduler):
        # todo: improve error handling
        print 'task did not complete'

        if hasattr(scheduler, 'units'):
            unit = scheduler.units.get(self)

            if unit is not None:
                print "* %s  state %s (%s), out/err: %s / %s" \
                      % (unit.uid,
                         unit.state,
                         unit.exit_code,
                         unit.stdout,
                         unit.stderr)

        if self.restartable and self.restart_failed:
            scheduler.submit(self)

    def _default_success(self, scheduler):
            print 'task succeeded. State:', self.state

            for f in self.modified_files:
                f.modified()
                scheduler.project.files.add(f)

            for f in self.targets:
                f.create(scheduler)
                scheduler.project.files.add(f)

    @property
    def description(self):
        task = self
        s = ['Task: %s [%s]' % (
                task.generator.__class__.__name__ or task.__class__.__name__, task.state)]

        if task.worker:
            s += ['Worker: %s:%s' % (task.worker.hostname, task.worker.cwd)]
            s += ['        cd worker.%s' % hex(task.__uuid__)]

        s += ['']
        s += ['Required : %s' % [x.short for x in task.unstaged_input_files]]
        s += ['Output : %s' % [x.short for x in task.targets]]
        s += ['Modified : %s' % [x.short for x in task.modified_files]]

        s += ['']
        s += ['<pretask>']
        s += map(str, task.pre_exec + [task.command] + task.post_exec)
        s += ['<posttask>']

        return '\n'.join(s)

    def fire(self, event, cluster):
        if event in Task._events:
            cbs = self._on.get(event, [])
            for cb in cbs:
                cb(self, cluster)

        if event in ['submit', 'fail', 'success']:
            self.state = event

    def is_done(self):
        return self.state in ['fail', 'success', 'cancelled']

    def was_successful(self):
        return self.state in ['success']

    def has_failed(self):
        return self.state in ['fail']

    def add_cb(self, event, cb):
        if event in Task._events:
            self._on[event] = self._on.get(event, [])
            self._on[event].append(cb)

    @property
    def additional_files(self):
        return self._add_files

    @property
    def command(self):
        cmd = self.executable or ''

        if isinstance(self.arguments, basestring):
            cmd += ' ' + self.arguments
        elif self.arguments is not None:
            cmd += ' '
            args = [
                a if (a[0] in ['"', "'"] and a[0] == a[-1]) else '"' + a + '"'
                for a in self.arguments]
            cmd += ' '.join(args)

        return cmd

    def add_files(self, files):
        if isinstance(files, File):
            self._add_files.append(files)
        elif isinstance(files, (list, tuple)):
            self._add_files += files

    @property
    def targets(self):
        """
        Return a set of all new and overwritten files

        Returns
        -------
        set of `File`
            the list of files that are created or overwritten by this task
        """
        return set(
            sum(filter(bool, [t.added for t in self._post_stage]), [])
            + self._add_files)

    @property
    def target_locations(self):
        """
        Return a set of all new and overwritten file urls

        Returns
        -------
        set of str
            the list of file urls that are created or overwritten by this task
        """
        return {x.url for x in self.targets}

    @property
    def sources(self):
        """
        Return a set of all required input files

        Returns
        -------
        set of `File`
            the list of files that are required by this task
        """
        return set(sum(filter(bool, [t.required for t in self._pre_stage]), []))

    @property
    def source_locations(self):
        """
        Return a set of all required file urls

        Returns
        -------
        set of str
            the list of file urls that are required by this task
        """
        return {x.url for x in self.sources}

    @property
    def new_files(self):
        """
        Return a set of all files the will be newly created by this task

        Returns
        -------
        set of `File`
            the set of files that are created by this task
        """

        outs = self.targets
        in_names = self.source_locations

        return {x for x in outs if x.url not in in_names}

    @property
    def modified_files(self):
        """
        A set of all input files whose names match output names and hence will be overwritten

        Returns
        -------
        list of `File`
            the list of potentially overwritten input files

        """
        ins = self.sources
        out_names = self.target_locations

        return {x for x in ins if x.url in out_names}

    @property
    def staged_files(self):
        """
        Set of all staged files by the tasks generator

        Returns
        -------
        set of `File`
            files that are staged by the tasks generator

        Notes
        -----
        There might be more files stages by other generators

        """
        if self.generator is not None:
            return set(sum(filter(bool, [t.required for t in self.generator.stage_in]), []))
        else:
            return {}

    @property
    def unstaged_input_files(self):
        """
        Return a set of `File` objects that are used but are not part of the generator stage

        Usually a task requires some reused files from staging and specific others.
        This function lists all the files that this task will stage to its working directory
        but will not be available from the set of staged files of the tasks generator

        Returns
        -------
        set of `File`
            the set of `File` objects that are needed and not staged

        """
        staged = self.staged_files
        reqs = self.sources

        return {r for r in reqs if r.url not in staged}

    def setenv(self, key, value):
        """
        Set an environment variable for the task

        Parameters
        ----------
        key : str
        value : str

        """
        if self._environment is None:
            self._environment = {key: value}
        elif key not in self._environment:
            self._environment[key] = value
        else:
            raise ValueError(
                'Cannot set same env variable `%s` more than once.' % key)

    def pre_bash(self, script):
        """
        Fills pre_exec

        Returns
        -------

        """
        if isinstance(script, (list, tuple)):
            script = sum(map(lambda x: x.split('\n'), script), [])
        elif isinstance(script, str):
            script = script.split('\n')

        self._user_pre_exec.extend(script)

    def post_bash(self, script):
        """
        Fill post_exec

        Returns
        -------

        """
        if isinstance(script, (list, tuple)):
            script = sum(map(lambda x: x.split('\n'), script), [])
        elif isinstance(script, str):
            script = script.split('\n')

        self._user_pre_exec.extend(script)

    def pre_stage(self, transaction):
        self._pre_stage.append(transaction)

    def post_stage(self, transaction):
        self._post_stage.append(transaction)

    def get(self, f, name=None):
        """
        Get a file and make it available to the task in the main directory

        Parameters
        ----------
        f : `File`
        name : `Location` or str

        Returns
        -------
        `File`
            the file instance of the file to be created in the unit

        """
        if f.drive in ['staging', 'sandbox', 'shared']:
            transaction = f.link(name)
        elif f.drive == 'file':
            transaction = f.transfer(name)
        elif f.drive == 'worker':
            if name is None:
                return f
            else:
                transaction = f.copy(name)
        else:
            raise ValueError(
                'Weird file location `%s` not sure how to get it.' %
                f.location)

        self.pre_stage(transaction)
        return transaction.target

    def link(self, f, name=None):
        transaction = f.link(name)
        self.pre_stage(transaction)
        return transaction.target

    def put(self, f, target):
        """
        Put a file back and make it persistent

        Corresponds to output_staging

        Parameters
        ----------
        f : `File`
            the file to be used
        target : str or `File`
            the target location. Need to contain a URL like `staging://` or
            `file://` for application side files

        """
        transaction = f.move(target)
        self.post_stage(transaction)
        return transaction.target

    def remove(self, f):
        """
        Remove a file at the end of the run

        Parameters
        ----------
        f : `File`

        """
        transaction = f.remove()
        self.post_stage(transaction)
        return transaction.source

    def call(self, command, *args, **kwargs):
        parts = command.split(' ')
        parts = [part.format(*args, **kwargs) for part in parts]
        self.executable = parts[0]
        self.arguments = parts[1:]

    def to_dict(self):
        dct = {c: getattr(self, c) for c in self._copy_attributes}

        return dct

    @classmethod
    def from_dict(cls, dct):
        task = cls()

        for c in cls._copy_attributes:
            setattr(task, c, dct.get(c))

        return task


class DummyTask(Task):
    """
    A Task not to be executed
    """

    def __init__(self):
        super(DummyTask, self).__init__()
        self.state = 'dummy'


class EnclosedTask(Task):
    """
    Wrap a task with additional staging, etc
    """
    _copies = [
        'executable', 'arguments',
        'environment', 'cores', 'mpi', 'stdout',
        'stderr', 'kernel', 'name', 'restartable', 'cleanup']

    def __init__(self, task, wrapper):
        super(Task, self).__init__()
        self._task = task
        self._wrapper = wrapper

    def __getattr__(self, item):
        if item in self._copies:
            return getattr(self._task, item)
        else:
            return getattr(self._wrapper, item)

    def to_dict(self):
        return {
            'task': self._task,
            'wrapper': self._wrapper
        }

    @property
    def environment(self):
        env = {}
        if self._wrapper.environment:
            env.update(self._wrapper.environment)
        if self._task.environment:
            env.update(self._task.environment)
        return env

    @classmethod
    def from_dict(cls, dct):
        return cls(dct['task'], dct['wrapper'])

    @property
    def input_staging(self):
        return self._wrapper.input_staging + self._task.input_staging

    @property
    def output_staging(self):
        return self._task.output_staging + self._wrapper.output_staging

    @property
    def pre_add_paths(self):
        return self._wrapper.pre_add_paths + self._task.pre_add_paths

    @property
    def pre_exec_tail(self):
        return self._wrapper.pre_exec_tail + self._task.pre_exec_tail

    @property
    def post_exec(self):
        return self._wrapper.post_exec + self._task.post_exec


class PythonTask(Task):
    """
    A special task that does a RPC python call
    """

    _copy_attributes = Task._copy_attributes + [
        '_python_import', '_python_source_files', '_python_function_name',
        '_python_args', '_python_kwargs', '_param_uid',
        '_rpc_input_file', '_rpc_output_file',
        'then_func_name']

    then_func = None

    def __init__(self, generator=None):
        super(PythonTask, self).__init__(generator)

        self._python_import = None
        self._python_source_files = None
        self._python_function_name = None
        self._python_args = None
        self._python_kwargs = None

        self.executable = 'python'
        self.arguments = '_run_.py'

        self._json = None
        self._param_uid = str(uuid.uuid4())

        self.then_func_name = 'then_func'

        self._rpc_input_file = \
            File('file://_rpc_input_%s.json' % self._param_uid)
        self._rpc_output_file = \
            File('file://_rpc_output_%s.json' % self._param_uid)

        self._task_pre_stage.append(
            self._rpc_input_file.transfer('input.json'))
        self._task_post_stage.append(
            File('output.json').transfer(self._rpc_output_file))

        f = File('staging:///_run_.py')
        self._task_pre_stage.append(f.link())

        self.add_cb('success', self.__class__._cb_success)
        self.add_cb('submit', self.__class__._cb_submit)

    def _cb_success(self, scheduler):
        # here is the logic to retrieve the result object
        filename = scheduler.replace_prefix(self._rpc_output_file.url)

        with open(filename, 'r') as f:
            data = scheduler.simplifier.from_json(f.read())

        if self.generator is not None and hasattr(self.generator, self.then_func_name):
            getattr(self.generator, self.then_func_name)(
                scheduler.project,
                data, {
                    'args': self._python_args,
                    'kwargs': self._python_kwargs})

        # remove the RPC file.
        os.remove(filename)
        os.remove(scheduler.replace_prefix(self._rpc_input_file.url))

    def _cb_submit(self, scheduler):
        filename = scheduler.replace_prefix(self._rpc_input_file.url)
        with open(filename, 'w') as f:
            f.write(scheduler.simplifier.to_json(self._get_json(scheduler)))

    def then(self, func_name):
        """
        Set the name of the function to be called from the generator after success

        Parameters
        ----------
        func_name : str
            the function name to be called after success

        """
        self.then_func_name = func_name

    def call(self, command, *args, **kwargs):
        """
        Set the python function to be called with its arguments

        Parameters
        ----------
        command : function
            a python function defined inside a package or a function. If in a
            package then the package needs to be installed on the cluster to be
            called. A function defined in a local file can be called as long
            as dependencies are installed.
        args : arguments to the function
        kwargs : named arguments to the function

        """
        self._python_function_name = '.'.join(
            [command.__module__, command.func_name])
        self._python_args = args
        self._python_kwargs = kwargs

        self._python_import, self._python_source_files = \
            get_function_source(command)

        for f in self._python_source_files:
            self._task_pre_stage.append(File('file://' + f).transfer())

    def _get_json(self, scheduler):
        dct = {
            'import': self._python_import,
            'function': self._python_function_name,
            'args': self._python_args,
            'kwargs': self._python_kwargs
        }
        return scheduler.flatten_location(dct)
