import os
import socket
import subprocess
import time
import sys
import random
import signal
import ctypes
import re
import shutil
from fcntl import fcntl, F_GETFL, F_SETFL

from mongodb import StorableMixin, SyncVariable, create_to_dict, ObjectSyncVariable

from scheduler import Scheduler
from reducer import StrFilterParser, WorkerParser, BashParser, PrefixParser
from logentry import LogEntry
from util import DT
from file import Transfer

import pymongo.errors

try:
    # works on linux
    libc = ctypes.CDLL("libc.so.6")
except OSError:
    libc = None


class WorkerScheduler(Scheduler):
    def __init__(self, resource, verbose=False):
        super(WorkerScheduler, self).__init__(resource)
        self._current_sub = None
        self._current_unit_dir = None
        self.current_task = None
        self.home_path = os.path.expanduser('~')
        self._done_tasks = set()
        self.state = 'booting'
        self._state_cb = None
        self._save_log_to_db = True
        self.verbose = verbose
        self._fail_after_each_command = True
        self._cleanup_successful = True

        self._std = {}

    @property
    def path(self):
        return self.resource.shared_path.replace('$HOME', self.home_path)

    @property
    def staging_area_location(self):
        return 'remote:///staging_area'

    @property
    def staging_area_location(self):
        return 'sandbox:///workers/staging_area'

    def task_to_script(self, task):
        # create a task that wraps errands from the resource and the scheduler as well

        wrapped_task = task >> self.wrapper >> self.project.resource.wrapper

        reducer = StrFilterParser() >> PrefixParser() >> WorkerParser() >> BashParser()

        script = reducer(self, wrapped_task.script)

        if self._fail_after_each_command:
            # make sure that a script exits if ANY command fails not just the last one
            script = ['set -e'] + script

        return script

    def submit(self, submission):
        """
        Submit a task in form of an event, a task or an taskable object

        Notes
        -----
        You can only

        Parameters
        ----------
        submission : (list of) [`Task` or `object` or `Event`]

        Returns
        -------
        list of `Task`
            the list of tasks actually executed after looking at all objects

        """
        tasks = self._to_tasks(submission)

        # filter all tasks that have not run yet
        # tasks = [t for t in tasks if t.__uuid__ not in self._done_tasks]

        if tasks:
            for task in tasks:
                # task.state = 'pending'
                self.tasks[task.__uuid__] = task

        return tasks

    @property
    def current_task_dir(self):
        if self._current_unit_dir is not None:
            return self.path + '/workers/' + self._current_unit_dir
        else:
            return None

    def _start_job(self, task):
        self._current_unit_dir = 'worker.%s' % hex(task.__uuid__)

        script_location = self.current_task_dir

        if os.path.exists(script_location):
            # the folder already exists, probably a failed previous attempt
            # a restart needs a clean folder so remove it now
            shutil.rmtree(script_location)

        # create a fresh folder
        os.makedirs(script_location)

        # and set the current directory
        os.chdir(script_location)

        task.fire('submit', self)

        script = self.task_to_script(task >> self.wrapper >> self.resource.wrapper)

        # write the script

        with open(script_location + '/running.sh', 'w') as f:
            f.write('\n'.join(script))

        task.state = 'running'
        task.fire(task.state, self)

        if libc is not None:
            def set_pdeathsig(sig=signal.SIGTERM):
                def death_fnc():
                    return libc.prctl(1, sig)

                return death_fnc

            preexec_fn = set_pdeathsig(signal.SIGTERM)
        else:
            preexec_fn = None

        self._current_sub = subprocess.Popen(
            ['/bin/bash', script_location + '/running.sh'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=preexec_fn, shell=False)

        # this is a special hack that allows to read from stdout and stderr
        # without a blocking `.read`, let's hope this works
        flags = fcntl(self._current_sub.stdout, F_GETFL)  # get current p.stdout flags
        fcntl(self._current_sub.stdout, F_SETFL, flags | os.O_NONBLOCK)

        flags = fcntl(self._current_sub.stderr, F_GETFL)  # get current p.stderr flags
        fcntl(self._current_sub.stderr, F_SETFL, flags | os.O_NONBLOCK)

        # prepare std catching
        self._start_std()

    def stop_current(self):
        if self._current_sub is not None:
            task = self.current_task
            self._current_sub.kill()
            del self.tasks[task.__uuid__]
            self._final_std()
            self.current_task = None

            return True
        else:
            return False

    def _start_std(self):
        self._std = {
            'stdout': '',
            'stderr': ''
        }

    def _advance_std(self):
        """
        Advance the stdout and stderr for some bytes, save it and redirect if desired

        """
        for s in ['stdout', 'stderr']:
            try:
                new_std = os.read(getattr(self._current_sub, s).fileno(), 1024)
                self._std[s] += new_std
                if self.verbose:
                    # send to stdout, stderr
                    std = getattr(sys, s)
                    std.write(new_std)
                    std.flush()

            except OSError:
                pass

    def _final_std(self):
        task = self.current_task
        try:
            out, err = self._current_sub.communicate()
            if self.verbose:
                sys.stderr.write(err)
                sys.stdout.write(out)

            # save full message
            stdout = self._std['stdout'] + out
            stderr = self._std['stderr'] + err

            if self._save_log_to_db:
                log_err = LogEntry(
                    'worker',
                    'stderr from running task',
                    stderr,
                    objs={'task': task}
                )
                log_out = LogEntry(
                    'worker',
                    'stdout from running task',
                    stdout,
                    objs={'task': task}
                )
                self.project.logs.add(log_err)
                self.project.logs.add(log_out)

                task.stdout = log_out
                task.stderr = log_err

        except ValueError:
            pass

    def advance(self):
        if self.current_task is None:
            if len(self.tasks) > 0:
                t = next(self.tasks.itervalues())
                self.current_task = t
                self._start_job(t)
        else:
            task = self.current_task
            # get current outputs
            return_code = self._current_sub.poll()

            # update current stdout and stderr by 1024 bytes

            self._advance_std()

            if return_code is not None:
                # finish std catching
                self._final_std()

                if return_code == 0:
                    # success

                    all_files_present = True
                    # see first if we have all claimed files for worker output staging transfer
                    for f in task.targets:
                        if isinstance(f, Transfer):
                            if not os.path.exists(self.replace_prefix(f.source.url)):
                                log = LogEntry(
                                    'worker',
                                    'execution error',
                                    'failed to create file before staging %s' % f.source.short,
                                    objs={'file': f, 'task': task}
                                )
                                self.project.logs.add(log)
                                all_files_present = False

                    if all_files_present:
                        try:
                            task.fire('success', self)
                            task.state = 'success'
                            print 'task succeeded'
                            if self._cleanup_successful:
                                print 'removing worker dir'
                                script_location = self.current_task_dir
                                if script_location is not None:
                                    shutil.rmtree(script_location)
                        except IOError:

                            task.state = 'fail'
                    else:
                        task.state = 'fail'
                else:
                    # failed
                    log = LogEntry(
                        'worker',
                        'task failed',
                        'see log files',
                        objs={'task': task}
                    )
                    self.project.logs.add(log)
                    task.state = 'failed'
                    try:
                        task.fire('fail', self)
                    except IOError:
                        pass

                    task.state = 'fail'

                del self.tasks[task.__uuid__]
                self._done_tasks.add(task.__uuid__)
                self._initialize_current()

    def release_queued_tasks(self):
        for t in list(self.tasks.values()):
            if t.state == 'queued':
                t.state = 'created'
                t.worker = None
                del self.tasks[t.__uuid__]

    def _initialize_current(self):
        self._current_sub = None
        self._current_unit_dir = None
        self.current_task = None

    def enter(self, project=None):
        self.change_state('booting')
        if project is not None:
            self.project = project

        # register this cluster with the session for later cleanup
        self.project.schedulers.add(self)

        # create main folders. make sure we can save project files
        self.stage_project()

        self.stage_generators()
        self.change_state('running')

    def stage_project(self):
        paths = [
            self.path + '/projects/',
            self.path + '/projects/' + self.project.name,
            self.path + '/projects/' + self.project.name + '/trajs']

        self._create_dirs(paths)

    @staticmethod
    def _create_dirs(paths):
        for p in paths:
            try:
                os.makedirs(p)
            except OSError:
                pass

    def stage_generators(self):
        paths = [
            self.path + '/workers',
            self.path + '/workers/staging_area'
            # self.path + '/workers/staging_area/trajs'
        ]

        self._create_dirs(paths)

        os.chdir(self.path + '/workers/staging_area/')

        reducer = StrFilterParser() >> PrefixParser() >> WorkerParser() >> BashParser()

        retries = 10
        while retries > 0:
            try:
                # todo: add staging that does some file copying as well
                for g in self.generators:
                    reducer(self, g.stage_in)

                retries = 0
            except OSError:
                time.sleep(random.random())
                retries -= 1

    def replace_prefix(self, path):
        # on a worker all runs on the remote side, so if we talk about file:// locations
        # we actually want them to work, once they are transferred. There are only two
        # ways this is supported (yet). Either the file is in the DB then we do not care
        # about the file location. The other case is, if the task generates it on the
        # file side and then transfers it. The trick we use is to just create the file
        # directly on the remote side and do the link as usual. The requires to alter
        # a file:// path to be on the remote side.

        # replace any occurance of `file://a/b/c/d/something` with `worker://_file_something
        path = re.sub(r"(file:\/\/[^ ]*\/)([^ \/]*)", r"worker://_file_\2", path)

        # call the default replacements
        path = super(WorkerScheduler, self).replace_prefix(path)
        return path

    def change_state(self, new_state):
        print 'changed state to', new_state
        self.state = new_state
        if self._state_cb is not None:
            self._state_cb(self)

    def shut_down(self, wait_to_finish=True):
        self.change_state('releaseunfinished')
        self.release_queued_tasks()

        if wait_to_finish:
            self.change_state('waitcurrent')
            curr = time.time()
            max_wait = 15
            while len(self.tasks) > 0 and time.time() - curr < max_wait:
                self.advance()
                time.sleep(2.0)

        # kill the current job
        self.change_state('shuttingdown')
        if self.current_task:
            if True:
                self.current_task.state = 'created'
            else:
                self.current_task.state = 'cancelled'
            self.stop_current()

        self.change_state('down')

    @property
    def is_idle(self):
        return len(self.tasks) == 0 and self.state == 'running'


class Worker(StorableMixin):

    _find_by = ['state', 'n_tasks', 'seen', 'verbose', 'prefetch', 'current']

    state = SyncVariable('state')
    n_tasks = SyncVariable('n_tasks')
    seen = SyncVariable('seen')
    verbose = SyncVariable('verbose')
    prefetch = SyncVariable('prefetch')
    command = SyncVariable('command')
    current = ObjectSyncVariable('current', 'tasks')

    def __init__(self, walltime=None, generators=None, sleep=None, heartbeat=None, prefetch=1,
                 verbose=False):
        super(Worker, self).__init__()
        self.hostname = socket.gethostname()
        self.cwd = os.getcwd()
        self.seen = time.time()
        self.walltime = walltime
        self.generators = generators
        self.sleep = sleep
        self.heartbeat = heartbeat
        self.prefetch = prefetch
        self.reconnect_time = 10
        self._scheduler = None
        self._project = None
        self.command = None
        self.verbose = verbose
        self.current = None
        self._last_current = None
        self.pid = os.getpid()

    to_dict = create_to_dict([
        'walltime', 'generators', 'sleep', 'heartbeat', 'hostname', 'cwd', 'seen', 'prefetch',
        'pid'
    ])

    @classmethod
    def from_dict(cls, dct):
        obj = super(Worker, cls).from_dict(dct)
        obj.hostname = dct['hostname']
        obj.cwd = dct['cwd']
        obj.seen = dct['seen']
        obj.pid = dct['pid']

        return obj

    def create(self, project):
        scheduler = WorkerScheduler(project.resource, self.verbose)
        scheduler._state_cb = self._state_cb
        self._scheduler = scheduler
        self._project = project
        scheduler.enter(project)

    def _state_cb(self, scheduler):
        self.state = scheduler.state

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def project(self):
        return self._project

    _running_states = ['running', 'waitandshutdown']
    _accepting_states = ['running']

    def _stop_current(self, mode):
        sc = self.scheduler
        task = sc.current_task

        if task:
            attempt = self.project.storage.tasks.modify_test_one(
                lambda x: x == task, 'state', 'running', 'stopping')
            if attempt is not None:
                if sc.stop_current():
                    # success, so mark the task as cancelled
                    task.state = mode
                    task.worker = None
                    print 'stopped a task [%s] from generator `%s` and set to `%s`' % (
                        task.__class__.__name__,
                        task.generator.name if task.generator else '---',
                        task.state)

            else:
                # seems that in the meantime the task has finished (success/fail)
                pass

    def execute(self, command):
        self.command = command

        # todo: add a wait here until worker responds with timeout

    def run(self):
        scheduler = self._scheduler
        project = self._project

        last = time.time()
        last_n_tasks = 0
        self.seen = last

        def task_test(x):
            return x.ready and (not self.generators or (
                hasattr(x.generator, 'name') and x.generator.name in self.generators))

        print 'up and running ...'

        try:
            reconnect = True

            while reconnect:
                reconnect = False
                try:
                    if len(scheduler.tasks) > 0:
                        # must have been a DB connection problem, attempt reconnection
                        print 'attempt reconnection'
                        self._project.reconnect()

                        print 'remove all pending tasks'
                        # remove all pending tasks as much as possible
                        for t in list(scheduler.tasks.values()):
                            if t is not scheduler.current_task:
                                if t.worker == self:
                                    t.state = 'created'
                                    t.worker = None

                                del scheduler.tasks[t.__uuid__]

                        # see, if we can salvage the currently running task
                        # unless it has been cancelled and is running with another worker
                        t = scheduler.current_task
                        if t.worker == self and t.state == 'running':
                            print 'continuing current task'
                            # seems like the task is still ours to finish
                            pass
                        else:
                            print 'current task has been captured. releasing.'
                            scheduler.stop_current()

                    # the main worker loop
                    while scheduler.state != 'down':
                        state = self.state
                        # check the state of the worker
                        if state in self._running_states:
                            scheduler.advance()
                            if scheduler.is_idle:
                                for _ in range(self.prefetch):
                                    tasklist = scheduler(
                                        project.storage.tasks.modify_test_one(
                                            task_test, 'state', 'created', 'queued'))

                                    for task in tasklist:
                                        task.worker = self
                                        print 'queued a task [%s] from generator `%s`' % (
                                            task.__class__.__name__,
                                            task.generator.name if task.generator else '---')

                                self.n_tasks = len(scheduler.tasks)

                        # handle commands
                        # todo: Place all commands in a separate store and consume ?!?
                        command = self.command

                        if command == 'shutdown':
                            # someone wants us to shutdown
                            scheduler.shut_down()

                        if command == 'kill':
                            # someone wants us to shutdown immediately. No waiting
                            scheduler.shut_down(False)

                        elif command == 'release':
                            scheduler.release_queued_tasks()

                        elif command == 'halt':
                            self._stop_current('halted')

                        elif command == 'cancel':
                            self._stop_current('cancelled')

                        elif command and command.startswith('!'):
                            result = subprocess.check_output(command[1:].split(' '))
                            project.logs.add(
                                LogEntry(
                                    'command', 'called `%s` on worker' % command[1:], result
                                )
                            )

                        if command:
                            self.command = None

                        if time.time() - last > self.heartbeat:
                            # heartbeat
                            last = time.time()
                            self.seen = last

                        time.sleep(self.sleep)
                        if self.walltime and time.time() - self.__time__ > self.walltime:
                            # we have reached the set walltime and will shutdown
                            print 'hit walltime of %s' % DT(self.walltime).length
                            scheduler.shut_down()

                        if scheduler.current_task is not self._last_current:
                            self.current = scheduler.current_task
                            self._last_current = self.current

                        n_tasks = len(scheduler.tasks)
                        if n_tasks != last_n_tasks:
                            self.n_tasks = n_tasks
                            last_n_tasks = n_tasks

                except (pymongo.errors.ConnectionFailure, pymongo.errors.AutoReconnect) as e:
                    print 'pymongo connection error', e
                    print 'try reconnection after %d seconds' % self.reconnect_time
                    # lost connection to DB, try to reconnect after some time
                    time.sleep(self.reconnect_time)
                    reconnect = True

        except KeyboardInterrupt:
            scheduler.shut_down()
            pass

    def shutdown(self, gracefully=True):
        self._scheduler.shut_down(gracefully)
