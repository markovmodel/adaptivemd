##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: Jan-Hendrik Prinz
#          John Ossyra
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
from __future__ import print_function, absolute_import

import os

import six
import uuid

from .file import File, JSONFile, FileTransaction
from .util import get_function_source
from .mongodb import StorableMixin, SyncVariable, ObjectSyncVariable


class BaseTask(StorableMixin):
    _copy_attributes = [
        '_main', '_add_paths', '_environment'
        ]

    def __init__(self):
        super(BaseTask, self).__init__()

        self._main = []

        self._add_paths = []
        self._environment = {}

    @staticmethod
    def _format_export_paths(paths):
        paths = sorted(list(set(paths)))
        return list(map('export PATH={}:$PATH'.format, paths))

    @staticmethod
    def _format_environment(env):
        if env:
            envs = [(key, env[key]) for key in sorted(list(env))]
            return ['export {0}={1}'.format(key, value) for key, value in envs]
        else:
            return []

    @property
    def pre_add_paths(self):
        """
        list of str
            the list of added paths to the $PATH variable by this task

        """
        return self._add_paths

    @property
    def environment(self):
        """
        dict str : str
            the dict of environment variables and their assigned value

        """
        return self._environment

    @property
    def pre_exec(self):
        """
        list of str or `Action`
            the list of actions to be run before the main script. Contains environment variables

        """
        return (
            self._format_export_paths(self.pre_add_paths) +
            self._format_environment(self.environment))

    @property
    def main(self):
        """
        list of str or `Action`
            the main part of the script

        """
        return (
            self._main
        )

    @property
    def script(self):
        """
        list of str or `Action`
            the full script of this task. This is what is send to a worker and parsed by it

        """
        return self.pre_exec + self.main

    def add_path(self, path):
        """

        Parameters
        ----------
        path : (list of) str
            a (list of) path(s) to be added to the $PATH variable before task execution

        """
        if isinstance(path, str):
            self._add_paths.append(path)
        elif isinstance(path, (list, tuple)):
            self._add_paths.extend(path)

    def __rshift__(self, other):
        """
        The `>>` can be used to wrap a task in one another.

        The outer task must have pre and post and the inner will use the full script

        Parameters
        ----------
        other : `PrePostTask`
            the task that wraps the current task

        Returns
        -------
        `EnclosedTask`
            the representation of a wrapped task

        """
        if other is None:
            return self
        elif isinstance(other, PrePostTask):
            return EnclosedTask(self, other)

    def to_dict(self):
        dct = {c: getattr(self, c) for c in self._copy_attributes}
        return dct

    @classmethod
    def from_dict(cls, dct):
        task = cls()

        for c in cls._copy_attributes:
            setattr(task, c, dct.get(c))

        return task


class Task(BaseTask):
    """
    A description for a task running on an HPC

    Attributes
    ----------
    worker : :class:`~adaptivemd.worker.WorkingScheduler`
        the currently assigned Worker instance (not the scheduler!)
    generator : :class:`~adaptivemd.generator.TaskGenerator`
        if given the :class:`~adaptivemd.generator.TaskGenerator` that
        was used to create this task
    state : str
        a string representing the current state of the execution. One of
        - 'created' : task has been created and is available for execution
        - 'running': task is currently executed by a scheduler
        - 'queued' : task has been captured by a worker for execution
        - 'fail' : task has completed but failed. You can restart it
        - 'success' : task has completed and succeeded.
        - 'halt' : task has been halted by user. You can restart it
        - 'cancelled' : task has been cancelled by user. You CANNOT restart it
    stdout : :class:`~adaptivemd.logentry.LogEntry`
        After completion you can access the stdout of the task here
    stderr : :class:`~adaptivemd.logentry.LogEntry`
        After completion you can access the stderr of the task here

    """
    _events = ['submit', 'fail', 'success', 'change']

    _copy_attributes = BaseTask._copy_attributes + [
        'stdout', 'stderr', 'restartable', 'cleanup',
        'generator', 'dependencies', 'state', 'worker',
        'est_exec_time', 'resource_requirements',
        'resource_name'
        ]

    _find_by = ['state', 'worker', 'stderr', 'stdout']

    state = SyncVariable('state', lambda x: x in ['success', 'cancelled'])
    worker = ObjectSyncVariable('worker', 'workers')
    stdout = ObjectSyncVariable('stdout', 'logs', lambda x: x is not None)
    stderr = ObjectSyncVariable('stderr', 'logs', lambda x: x is not None)

    FINAL_STATES = ['success', 'cancelled']
    # TODO change halted  to paused
    #      find where else this needs to change
    RESTARTABLE_STATES = ['fail', 'halted']
    RUNNABLE_STATES = ['created']

    def __init__(self, generator=None, resource_name=None, est_exec_time=5,
                 cpu_threads=1, gpu_contexts=0, mpi_rank=0):

        super(Task, self).__init__()

        self.generator = generator
        self.dependencies = None
        self._on = {}
        self._add_files = []

        self.stdout = None
        self.stderr = None

        self.restartable = None
        self.cleanup = None
        self.restart_failed = False

        self.add_cb('fail', self.__class__._default_fail)
        self.add_cb('success', self.__class__._default_success)

        self.state = 'created'

        self.worker = None

        assert isinstance(cpu_threads, int)
        assert isinstance(gpu_contexts, int)
        assert isinstance(mpi_rank, int)

        if isinstance(resource_name, str):
            resource_name = [resource_name]

        self.resource_name = resource_name

        self.resource_requirements = {'cpu_threads': cpu_threads,
                                      'gpu_contexts': gpu_contexts,
                                      'mpi_rank': mpi_rank}

        assert isinstance(est_exec_time, int)
        self.est_exec_time = est_exec_time

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
        """
        Check if all dependency tasks are successful

        Returns
        -------
        bool
            True if all dependencies are fulfilled
        """
        dependencies = self.dependencies
        if dependencies is not None:
            return all(d.state == 'success' for d in self.dependencies)

        return True

    @property
    def ready(self):
        """
        Check if this task is ready to be executed

        Usually this only checks dependencies but might involve more elaborate checks
        for specific Task classes

        Returns
        -------
        bool
            if True the task can now be executed

        """
        if self.dependencies:
            return self.dependency_okay

        return True

    def _default_fail(self, scheduler, path=None):
        """
        the default function executed when a task fails

        You can add your own callbacks. This is just the default

        Parameters
        ----------
        scheduler : `Scheduler`
            the calling scheduler to know where the task has failed

        """
        # todo: improve error handling
        print('task did not complete')

        if hasattr(scheduler, 'units'):
            unit = scheduler.units.get(self)

            if unit is not None:
                print("* %s  state %s (%s), out/err: %s / %s"
                       % (unit.uid,
                          unit.state,
                          unit.exit_code,
                          unit.stdout,
                          unit.stderr))

    def _default_success(self, scheduler, path=None):
        """
        the default function executed when a task succeeds

        You can add your own callbacks. This is just the default

        Parameters
        ----------
        scheduler : `Scheduler`
            the calling scheduler to know where the task has succeeded

        """

        for f in self.modified_files:
            f.modified()
            scheduler.project.files.add(f)

        for f in self.targets:
            f.create(scheduler)
            scheduler.project.files.add(f)

    @property
    def description(self):
        """
        Return a lengthy description of the task for debugging and information

        Returns
        -------
        str
            the information text
        """
        task = self
        s = ['Task: %s(%s) [%s]' % (
                task.__class__.__name__, task.generator.__class__.__name__, task.state)]

        if task.worker:
            s += ['Worker: %s:%s' % (task.worker.hostname, task.worker.cwd)]
            s += ['        cd worker.%s' % hex(task.__uuid__)]

        s += ['']
        s += ['Sources\n-- Unstaged']
        s += ['- %s %s' % (x.short, '[exists]' if x.exists else '')
              for x in task.unstaged_input_files]
        s += ['-- Staged']
        s += ['- %s %s' % (x.short, '[exists]' if x.exists else '')
              for x in task.sources if x not in task.unstaged_input_files]
        s += ['\nTargets']
        s += ['- %s' % x.short for x in task.targets]
        s += ['\nModified']
        s += ['- %s' % x.short for x in task.modified_files]

        s += ['']
        #s += ['<pretask>']
        #s += list(map(str, task.pretask))
        #s += ['<main>']
        s += list(map(str, task.script))
        #s += ['<posttask>']
        #s += list(map(str, task.pretask))

        return '\n'.join(s)

    def fire(self, event, scheduler, path=None):
        """
        Fire an event like success or failed.

        Notes
        -----
        You should never have to call this yourself. The scheduler does that.

        Parameters
        ----------
        event : str
            the events name like `fail`, `success`, `submit`
        scheduler : `Scheduler`
            the scheduler that issued the events to be fired

        """
        if event in Task._events:
            cbs = self._on.get(event, [])
            for cb in cbs:
                cb(self, scheduler, path)

        if event in ['submit', 'fail', 'success']:
            self.state = event

    def is_done(self):
        """
        Check if the task is done executing. Can be failed, successful or cancelled

        Returns
        -------
        bool
            True if the task has finished its execution

        """
        # TODO use final states attribute
        if self.state in ['fail', 'success', 'cancelled']:
            return True

        else:
            return False

    def was_successful(self):
        """
        Check if the task is done executing and was successful

        Returns
        -------
        bool
            True if the task has finished successfully

        """
        return self.state in ['success']

    def has_failed(self):
        """
        Check if the task is done executing and has failed

        Returns
        -------
        bool
            True if the task has finished but failed

        """
        return self.state in ['fail']

    def add_cb(self, event, cb):
        """
        Add a custom callback

        Parameters
        ----------
        event : str
            name of the event to be called upon firing
        cb : function
            the function to be called. It must be a function that takes a task and a scheduler

        """
        if event in Task._events:
            self._on[event] = self._on.get(event, [])
            self._on[event].append(cb)

    @property
    def additional_files(self):
        """
        list of `Location`
            return the list of files created other than taken care of by actions. Should usually not
            be necessary. If you do some bad hacks with the bash you can add files that
            you transferred yourself to the project folders.

        """
        return self._add_files

    def add_files(self, files):
        """
        Add additional files to the task execution

        Should usually not be necessary. If you do some bad hacks with the bash you
        can add files that you transferred yourself to the project folders.

        Parameters
        ----------
        files : list of `File`
            the list of files to be added to the task

        """
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

        transactions = [t for t in self.script if isinstance(t, FileTransaction)]

        return [x for x in set(sum(filter(bool, [f.added for f in transactions]), []) + self._add_files) if not x.is_temp]

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
        transactions = [t for t in self.script if isinstance(t, FileTransaction)]

        return [x for x in set(sum(filter(bool, [t.required for t in transactions]), []) + self._add_files) if not x.is_temp]

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
            return set(filter(bool, [t.target.url for t in self.generator.stage_in]))
        else:
            return set()

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

    def append(self, cmd):
        """
        Append a command to this task

        Returns
        -------

        """
        self._main.append(cmd)

    def prepend(self, cmd):
        """
        Append a command to this task

        Returns
        -------

        """
        self._main.insert(0, cmd)

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

        self.append(transaction)

        assert isinstance(transaction, FileTransaction)
        return transaction.target

    def touch(self, f):
        """
        Add an action to create an empty file or folder at a given location

        Parameters
        ----------
        f : `Location`
            the location (file or folder) to be used

        """
        transaction = f.touch()
        self.append(transaction)
        return transaction.source

    def link(self, f, name=None):
        """
        Add an action to create a link to a file (under a new name)

        Parameters
        ----------
        f : `Location`
            the source location (file or folder) to be used
        name : `Location` or str
            the target location to be used. For source files and target folders the
            basename is copied

        Returns
        -------
        `Location`
            the actual target location

        """
        transaction = f.link(name)
        self.append(transaction)
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

        Returns
        -------
        `Location`
            the actual target location

        """
        transaction = f.move(target)
        self.append(transaction)
        return transaction.target

    def remove(self, f):
        """
        Add an action to remove a file or folder

        Parameters
        ----------
        f : `File`
            the location to be removed

        Returns
        -------
        `Location`
            the actual location

        """
        transaction = f.remove()
        self.append(transaction)
        return transaction.source

    def add_conda_env(self, name, activate_prefix=None):
        #TODO sort out this resource.wrapper.append() business
        #     clearly its not happening, is it possible?
        #      - use as option
        """
        Add loading a conda env as the first command, with source
        deactivate as the final command. Currently this is best done
        as a final step in defining the task objects.

        This calls `resource.wrapper.append('source activate {name}')`
        Parameters
        ----------
        name : str
            name of the conda environment

        """
        prefix = ''
        if activate_prefix:
            prefix = os.path.join(activate_prefix, prefix)

        self.prepend('source {p}activate {n}'.format(p=prefix, n=name))
        self.append('source deactivate')

    def add_virtualenv(self, activate_location):
        """
        Add activation of virtualenv as the first command, with deactivate
        as the final command. Currently this is best done as
        a final step in defining the task objects.

        Parameters
        ----------
        activate_location : 
            Full file location of the virtualenv activate script
        """
        self.prepend('source ' + activate_location)
        self.append('deactivate')


class PrePostTask(Task):
    """
    Special task where the script is devided into Pre/Main/Post

    Attributes
    ----------
    pre : list
        the pre part of the script. Attach actions with `.append`
    post : list
        the post part of the script. Attach actions with `.append`

    """

    _copy_attributes = Task._copy_attributes + [
        'pre', 'post'
    ]

    def __init__(self, generator=None, resource_name=None,
                 est_exec_time=5, cpu_threads=1,
                 gpu_contexts=0, mpi_rank=0):

        super(PrePostTask, self).__init__(generator, resource_name,
                                          est_exec_time, cpu_threads,
                                          gpu_contexts, mpi_rank)

        self.pre = []
        self.post = []

    def pre_link(self, f, name=None):
        """
        Add an action to create a link to a file (under a new name)

        Parameters
        ----------
        f : `Location`
            the source location (file or folder) to be used
        name : `Location` or str
            the target location to be used. For source files and target folders the
            basename is copied

        Returns
        -------
        `Location`
            the actual target location

        """
        transaction = f.link(name)
        self.pre.append(transaction)
        return transaction.target

    def post_put(self, f, target):
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

        Returns
        -------
        `Location`
            the actual target location

        """
        transaction = f.move(target)
        self.post.append(transaction)
        return transaction.target

    @property
    def pre_exec(self):
        return (
            self._format_export_paths(self.pre_add_paths) +
            self._format_environment(self.environment))

    @property
    def main(self):
        return self.pre + self._main + self.post

    def add_conda_env(self, name, activate_prefix=None):
        #TODO sort out this resource.wrapper.append() business
        #     clearly its not happening, is it possible?
        #      - use as option
        """
        Add loading a conda env as the first command, with source
        deactivate as the final command. Currently this is best done
        as a final step in defining the task objects.

        This calls `resource.wrapper.append('source activate {name}')`
        Parameters
        ----------
        name : str
            name of the conda environment

        """
        activate   = 'activate'
        deactivate = 'deactivate'
        if activate_prefix:
            activate   = os.path.join(activate_prefix, activate)
            deactivate = os.path.join(activate_prefix, deactivate)

        self.pre.insert(0,'source {a} {n}'.format(a=activate, n=name))
        self.post.append('source {d}'.format(d=deactivate))

    def add_virtualenv(self, activate_location):
        """
        Add activation of virtualenv as the first command, with deactivate
        as the final command. Currently this is best done as
        a final step in defining the task objects.

        Parameters
        ----------
        activate_location : 
            Full file location of the virtualenv activate script
        """
        self.pre.insert(0,'source ' + activate_location)
        self.post.append('deactivate')


class MPITask(PrePostTask):
    """
    A description for a task running on an HPC with MPI (used for RP)

    """

    _copy_attributes = PrePostTask._copy_attributes + [
        'executable', 'arguments',
        'cores', 'mpi', 'kernel', 'name'
    ]

    def __init__(self, generator=None):
        super(MPITask, self).__init__(generator)

        self.executable = None
        self.arguments = None

        self.cores = 1
        self.mpi = False

        self.kernel = None
        self.name = None

    @property
    def command(self):
        cmd = self.executable or ''

        if isinstance(self.arguments, six.string_types):
            cmd += ' ' + self.arguments
        elif self.arguments is not None:
            cmd += ' '
            args = [
                a if (a[0] in ['"', "'"] and a[0] == a[-1]) else '"' + a + '"'
                for a in self.arguments]
            cmd += ' '.join(args)

        return cmd

    def call(self, command, *args, **kwargs):
        parts = command.split(' ')
        parts = [part.format(*args, **kwargs) for part in parts]
        self.executable = parts[0]
        self.arguments = parts[1:]

    @property
    def main(self):
        return self.pre + [self.command] + self.post

    def append(self, cmd):
        raise RuntimeWarning(
            'append does nothing for MPITasks. Use .pre.append or .post.append')

    def prepend(self, cmd):
        raise RuntimeWarning(
            'prepend does nothing for MPITasks. Use .pre.prepend or .post.prepend')


class DummyTask(PrePostTask):
    """
    A Task not to be executed. Only to be wrapped around other tasks
    """

    def __init__(self):
        super(DummyTask, self).__init__()
        self.state = 'dummy'

    @property
    def description(self):
        task = self
        s = ['Task: %s' % task.__class__.__name__]

        s += ['<pre>']
        s += list(map(str, task.pre_exec + task.pre))
        s += ['</pre>']
        s += ['<main />']
        s += ['<post>']
        s += list(map(str, task.post))
        s += ['</post>']

        return '\n'.join(s)


class EnclosedTask(Task):
    """
    Helper class to wrap any task with a PrePostTask
    """
    _copies = [
        'environment', 'stdout', 'stderr', 'restartable', 'cleanup']

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

    @property
    def pre_add_paths(self):
        return self._wrapper.pre_add_paths + self._task.pre_add_paths

    @classmethod
    def from_dict(cls, dct):
        return cls(dct['task'], dct['wrapper'])

    @property
    def main(self):
        return self._wrapper.pre + self._task.main + self._wrapper.post


class PythonTask(PrePostTask):
    """
    A special task that does a RPC python calls

    Attributes
    ----------
    then_func_name : str or None
        the name of the function of the `TaskGenerator` to be called with
        the resulting output
    store_output : bool
        if True then the result from the RPC called function will also be
        stored in the database. It can later be retrieved using the `.output`
        attribute on the task completed successfully
    """

    _copy_attributes = PrePostTask._copy_attributes + [
        '_python_import', '_python_source_files', '_python_function_name',
        '_python_args', '_python_kwargs', 'output_stored',
        '_rpc_input_file', '_rpc_output_file',
        'then_func_name', 'store_output']

    then_func = None
    output_stored = SyncVariable('output_stored', lambda x: isinstance(x, bool))

    def __init__(self, generator=None, resource_name=None,
                 est_exec_time=5, cpu_threads=1, 
                 gpu_contexts=0, mpi_rank=0):

        super(PythonTask, self).__init__(generator, resource_name,
                                          est_exec_time, cpu_threads,
                                          gpu_contexts, mpi_rank)

        self._python_import = None
        self._python_source_files = None
        self._python_function_name = None
        self._python_args = None
        self._python_kwargs = None
        self.output_stored = False

        # self.executable = 'python'
        # self.arguments = '_run_.py'

        self.then_func_name = 'then_func'

        self._rpc_input_file = \
            JSONFile('file://_rpc_input_%s.json' % hex(self.__uuid__))
        self._rpc_output_file = \
            JSONFile('file://_rpc_output_%s.json' % hex(self.__uuid__))

        # input args -> input.json
        self.pre.append(self._rpc_input_file.transfer('input.json'))

        # output data -> output.json
        self.post.append(File('output.json').transfer(self._rpc_output_file))

        f = File('staging:///_run_.py')
        self.pre.append(f.link())

        self.add_cb('success', self.__class__._cb_success)
        self.add_cb('submit', self.__class__._cb_submit)

        # if True the RPC result will be stored in the DB with the task
        self.store_output = True

    def backup_output_json(self, target):
        """
        Add an action that will copy the resulting JSON file to the given path

        Parameters
        ----------
        target : `Location`
            the place to copy the resulting `output.json` file to

        """
        self.post.append(File('output.json').copy(target))

    def set_output_stored(self, project, is_stored):
        my_id = str(uuid.UUID(int=self.__uuid__))
        project.storage.tasks._document.update_one({"_id": my_id},
            {"$set": {"_dict.output_stored": is_stored}})

   ### @property
   ### def output_stored(self):
   ###     return self._output_stored

   ### @output_stored.setter
   ### #def output_stored(self, project_isstored):
   ### def output_stored(self, is_stored):
   ###     # TODO WHY can't we just do this:
   ###     print(is_stored, is_stored.__class__)
   ###     assert isinstance(is_stored, bool)
   ###     self._output_stored = is_stored
   ###     #project, isstored = project_isstored
   ###     #my_id = str(uuid.UUID(int=self.__uuid__))
   ###     #project.storage.tasks._document.update_one({"_id": my_id},
   ###     #    {"$set": {"_dict._output_stored": isstored}})
   ### def mark_output_stored(self, project, is_stored):
   ###     my_id = str(uuid.UUID(int=self.__uuid__))
   ###     project.storage.tasks._document.update_one({"_id": my_id},
   ###         {"$set": {"_dict._output_stored": is_stored}})
   ###  
    def _cb_success(self, scheduler, path=None):
        # here is the logic to retrieve the result object
        # the output file is a JSON and these know how to load itself

        if self.store_output:
            # by default store the result. If you handle it yourself you
            # might want to turn it off to not save the data twice
            self._rpc_output_file.load(scheduler, path)

        data = self._rpc_output_file.get(scheduler, path)

        if self.generator is not None and hasattr(self.generator, self.then_func_name):

            # Data given to DB Here with function named `then_func_name`
            getattr(self.generator, self.then_func_name)(
                scheduler.project, self, data, self._python_kwargs)

            #self.output_stored = tuple([scheduler.project, True])
            self.set_output_stored(scheduler.project, True)

        # cleanup
        # mark as changed / deleted
        if not path:
            filename = scheduler.get_path(self._rpc_output_file)
            os.remove(filename)
            self._rpc_output_file.modified()
            os.remove(scheduler.get_path(self._rpc_input_file))
            self._rpc_input_file.modified()

    def _cb_submit(self, scheduler, path=None):
        filename = scheduler.replace_prefix(self._rpc_input_file.url)
        with open(filename, 'w') as f:
            f.write(scheduler.simplifier.to_json(self._get_json(scheduler)))

    @property
    def output(self):
        """
        Return the data contained in the output file

        Returns
        -------
        object

        """
        return self._rpc_output_file.data

    def then(self, func_name):
        """
        Set the name of the function to be called from the generator after success

        Parameters
        ----------
        func_name : str
            the function name to be called after success

        """
        self.then_func_name = func_name

    def call(self, command, **kwargs):
        """
        Set the python function to be called with its arguments

        Parameters
        ----------
        command : function
            a python function defined inside a package or a function. If in a
            package then the package needs to be installed on the cluster to be
            called. A function defined in a local file can be called as long
            as dependencies are installed.
        kwargs : ``**kwargs``
            named arguments to the function

        """
        self._python_function_name = '.'.join([command.__module__, command.__name__])

        self._python_kwargs = kwargs

        self._python_import, self._python_source_files = \
            get_function_source(command)

        for f in self._python_source_files:
            self.pre.append(File('file://' + f).load().transfer())

        # call the helper script to execute the function call
        self.append('python _run_.py')

    def _get_json(self, scheduler):
        dct = {
            'import': self._python_import,
            'function': self._python_function_name,
            'kwargs': self._python_kwargs,
            'project': scheduler.project.name,
            'generator': self.generator.name
        }
        return scheduler.flatten_location(dct)
