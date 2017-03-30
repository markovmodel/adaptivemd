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


import threading
import time
import numpy as np
import os
import types

from file import URLGenerator, File
from engine import Trajectory
from bundle import StoredBundle
from condition import Condition
from resource import Resource
from generator import TaskGenerator
from model import Model
from task import Task
from worker import Worker
from logentry import LogEntry
from plan import ExecutionPlan

from mongodb import MongoDBStorage, ObjectStore, FileStore, DataDict, WeakValueCache


import logging
logger = logging.getLogger(__name__)


class Project(object):
    """
    A simulation project

    Attributes
    ----------

    Notes
    -----

    You will later create `Scheduler` objects that explicitly correspond to
    a specific cue on a specific cluster that is accessible from within this
    shared FS resource.

    Attributes
    ----------

    name : str
        a short descriptive name for the project. This name will be used in the
        database creation also.
    resource : `Resource`
        a resource to run the project on. The resource specifies the memory
        storage location. Not necessarily which cluster is used. An example is,
        if at an institute several clusters (CPU, GPU) share the same shared FS.
        If clusters use the same FS you can run simulations across clusters
        without problems and so so this resource is the most top-level
        limitation.
    files : :class:`Bundle`
        a set of file objects that are available in the project and are
        believed to be available within the resource as long as the project
        lives
    trajectories : `ViewBundle`
        all `File` object that are of `Trajectory` type and which have a
        positive `created` attribute. This means the file was really created
        and has not been altered yet.
    workers : `Bundle`
        a set of all registered `Worker` instanced in the project
    files : `Bundle`
        a set of file objects that are available in the project and are
        believed to be available within the resource as long as the project
        lives
    models : `Bundle`
        a set of stored models in the DB
    tasks : `Bundle`
        a set of all queued `Task`s in the project
    logs : `Bundle`
        a set of all stored log entries
    data : `Bundle`
        a set of `DataDict` objects that represent completely stored files in
        the database of arbitrary size
    schedulers : set of `Scheduler`
        a set of attached schedulers with controlled shutdown and reference
    storage : `MongoDBStorage`
        the mongodb storage wrapper to access the database of the project
    _worker_dead_time : int
        the time after which an unresponsive worker is considered dead. Its
        tasks will be assigned the state set in
        :attr:`_set_task_state_from_dead_workers`.
        Default is 60s. Make sure that
        the heartbeat of a worker is much less that this.
    _set_task_state_from_dead_workers : str
        if a worker is dead then its tasks are assigned this state. Default is
        ``created`` which means the task will be restarted by another worker.
        You can also chose ``halt`` or ``cancelled``. See `Task` for details

    See also
    --------
    `Task`

    """

    def __init__(self, name):
        self.name = name

        self.session = None
        self.pilot_manager = None
        self.schedulers = set()

        self.models = StoredBundle()
        self.generators = StoredBundle()
        self.files = StoredBundle()
        self.tasks = StoredBundle()
        self.workers = StoredBundle()
        self.logs = StoredBundle()
        self.data = StoredBundle()
        # self.commands = StoredBundle()
        self.resource = None

        self._all_trajectories = self.files.c(Trajectory)
        self.trajectories = self._all_trajectories.v(lambda x: x.created > 0)

        self._events = []

        # generator for trajectory names
        self.traj_name = URLGenerator(
            os.path.join(
                'sandbox:///projects/',
                self.name,
                'trajs',
                '{count:08d}',
                ''))

        self.storage = None

        self._client = None
        self._open_db()

        self._lock = threading.Lock()
        self._event_timer = None
        self._stop_event = None

        # timeout if a worker is not changing its heartbeat in the last n seconds
        self._worker_dead_time = 60

        # tasks from dead workers that were started or queue should do what?
        self._set_task_state_from_dead_workers = 'created'

        # instead mark these as failed and decide manually
        # self._set_task_state_from_dead_workers = 'fail'

        # or do not care. This is fast but not recommended
        # self._set_task_state_from_dead_workers = None

    def initialize(self, resource):
        """
        Initialize a project with a specific resource.

        Notes
        -----
        This should only be called to setup the project and only the very
        first time.

        Parameters
        ----------
        resource : `Resource`
            the resource used in this project

        """
        self.storage.close()

        self.resource = resource

        st = MongoDBStorage(self.name, 'w')
        # st.create_store(ObjectStore('objs', None))
        st.create_store(ObjectStore('generators', TaskGenerator))
        st.create_store(ObjectStore('files', File))
        st.create_store(ObjectStore('resources', Resource))
        st.create_store(ObjectStore('models', Model))
        st.create_store(ObjectStore('tasks', Task))
        st.create_store(ObjectStore('workers', Worker))
        st.create_store(ObjectStore('logs', LogEntry))
        st.create_store(FileStore('data', DataDict))
        # st.create_store(ObjectStore('commands', Command))

        st.save(self.resource)

        st.close()

        self._open_db()

    def _open_db(self):
        # open DB and load status
        self.storage = MongoDBStorage(self.name)

        if hasattr(self.storage, 'tasks'):
            self.files.set_store(self.storage.files)
            self.generators.set_store(self.storage.generators)
            self.models.set_store(self.storage.models)
            self.tasks.set_store(self.storage.tasks)
            self.workers.set_store(self.storage.workers)
            self.logs.set_store(self.storage.logs)
            self.data.set_store(self.storage.data)
            # self.commands.set_store(self.storage.commands)
            self.resource = self.storage.resources.find_one({})

            self.storage.files.set_caching(True)
            self.storage.models.set_caching(WeakValueCache())
            self.storage.generators.set_caching(True)
            self.storage.tasks.set_caching(True)
            self.storage.workers.set_caching(True)
            self.storage.resources.set_caching(True)
            self.storage.data.set_caching(WeakValueCache())
            self.storage.logs.set_caching(WeakValueCache())

            # make sure that the file number will be new
            self.traj_name.initialize_from_files(self.trajectories)

    def reconnect(self):
        """
        Reconnect the DB

        """
        self._open_db()

    def _close_db(self):
        self.storage.close()

    def close_rp(self):
        """
        Close the RP session

        Before using RP you need to re-open and then you will run in a
        new session.

        """
        self._close_rp()

    def _close_rp(self):
        for r in set(self.schedulers):
            r.shut_down(False)

        # self.report.header('finalize')
        if self.session is not None and not self.session.closed:
            self.session.close()

        self.files.close()
        self.generators.close()
        self.models.close()

    @classmethod
    def list(cls):
        """
        List all projects in the DB

        Returns
        -------
        list of str
            a list of all project names

        """
        storages = MongoDBStorage.list_storages()
        return storages

    @classmethod
    def delete(cls, name):
        """
        Delete a complete project

        Notes
        -----
        Attention!!!! This cannot be undone!!!!

        Parameters
        ----------
        name : str
            the project name to be deleted

        """
        MongoDBStorage.delete_storage(name)

    def get_scheduler(self, name=None, **kwargs):
        """

        Parameters
        ----------
        name : str
            name of the scheduler class provided by the `Resource` used in
            this project. If None (default) the cluster/queue ``default`` is
            used that needs to be implemented for every resource

        kwargs : ``**kwargs``
            Additional arguments to initialize the cluster scheduler provided
            by the `Resource`

        Notes
        -----
        the scheduler is automatically entered/opened so the pilot jobs is
        submitted to the queueing system and it counts against your
        simulation time! If you do not want to do so directly. Create
        the `Scheduler` by yourself and later call ``scheduler.enter(project)``
        to start using it. To close the scheduler call ``scheduler.exit()``

        Returns
        -------
        `Scheduler`
            the scheduler object that can be used to execute tasks on that
            cluster/queue
        """
        # get a new scheduler to submit tasks
        if name is None:
            scheduler = self.resource.default()
        else:
            scheduler = getattr(self.resource, name)(**kwargs)

        # and prepare the scheduler
        scheduler.enter(self)

        # add the task generating capabilities to the scheduler
        map(scheduler.has, self.generators)

        scheduler.stage_generators()

        return scheduler

    def close(self):
        """
        Close the project and all related sessions and DB connections

        """
        self._close_rp()
        self._close_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        fail = True
        if exc_type is None:
            pass
        elif issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            # self.report.warn('exit requested\n')
            pass
        elif issubclass(exc_type, Exception):
            # self.report.error('caught exception: %s\n' % exc_type)
            fail = False

        self.close()

        return fail

    def queue(self, *tasks):
        """
        Submit jobs to the worker queue

        Parameters
        ----------
        tasks : (list of) `Task` or `Trajectory`
            anything that can be run like a `Task` or a `Trajectory` with engine

        """
        for task in tasks:
            if isinstance(task, Task):
                self.tasks.add(task)
            elif isinstance(task, (list, tuple)):
                map(self.queue, task)
            elif isinstance(task, Trajectory):
                if task.engine is not None:
                    t = task.run()
                    if t is not None:
                        self.tasks.add(t)

            # else:
            #     # if the engines can handle some object we parse these into tasks
            #     for cls, gen in self.file_generators.items():
            #         if isinstance(task, cls):
            #             return self.queue(gen(task))

            # we do not allow iterators, too dangerous
            # elif hasattr(task, '__iter__'):
            #     map(self.tasks.add, task)

    # @property
    # def file_generators(self):
    #     """
    #     Return a list of file generators the convert certain objects into task
    #
    #     Returns
    #     -------
    #     dict object : function -> (list of) `Task`
    #     """
    #     d = {}
    #     for gen in self.generators:
    #         d.update(gen.file_generators())
    #
    #     return d

    def new_trajectory(self, frame, length, engine=None, number=1):
        """
        Convenience function to create a new `Trajectory` object

        It will use incrementing numbers to create trajectory names used in
        the engine executions. Use this function to always get an unused
        trajectory name.

        Parameters
        ----------
        frame : `File` or `Frame`
            if given a `File` it is assumed to be a ``.pdb`` file that contains
            initial coordinates. If a frame is given one assumes that this
            `Frame` is the initial structure / frame zero in this trajectory
        length : int
            the length of the trajectory
        engine : `Engine` or None
            the engine used to generate the trajectory. The engine contains all
            the specifics about the trajectory internal structure since it is the
            responsibility of the engine to really create the trajectory.
        number : int
            the number of trajectory objects to be returned. If ``1`` it will be
            a single object. Otherwise a list of `Trajectory` objects.

        Returns
        -------
        `Trajectory` or list of `Trajectory`

        """
        if number == 1:
            traj = Trajectory(next(self.traj_name), frame, length, engine)
            return traj

        elif number > 1:
            return [self.new_trajectory(frame, length, engine) for _ in range(number)]

    def on_ntraj(self, numbers):
        """
        Return a condition that is true as soon a the project has n trajectories

        Parameters
        ----------
        numbers : int or iterator of int
            either a single int or an iterator that returns several ints

        Returns
        -------
        `NTrajectories` or generator of `NTrajectories`
            the single condition or a generator of conditions matching the ints
            in the iterator

        """
        if hasattr(numbers, '__iter__'):
            return (NTrajectories(self, n) for n in numbers)
        else:
            return NTrajectories(self, numbers)

    def on_nmodel(self, numbers):
        """
        Return a condition representing the reach of a certain number of models

        Parameters
        ----------
        numbers : int or iterator of int
            the number(s) of the models to be reached

        Returns
        -------
        (generator of) `Condition`
            a (list of) `Condition`
        """
        if hasattr(numbers, '__iter__'):
            return (NModels(self, n) for n in numbers)
        else:
            return NModels(self, numbers)

    # todo: move to brain
    def find_ml_next_frame(self, n_pick=10):
        """
        Find initial frames picked by inverse equilibrium distribution

        This is the simplest adaptive strategy possible. Start from the
        states more likely if a state has not been seen so much. Effectively
        stating that less knowledge of a state implies a higher likelihood to
        find a new state.

        Parameters
        ----------
        n_pick : int
             number of returned trajectories

        Returns
        -------
        list of `Frame`
            the list of trajectories with the selected initial points.
        """
        if len(self.models) > 0:
            model = self.models.last

            assert(isinstance(model, Model))
            data = model.data

            n_states = data['clustering']['k']
            modeller = data['input']['modeller']

            outtype = modeller.outtype

            # the stride of the analyzed trajectories
            used_stride = modeller.engine.types[outtype].stride

            # all stride for full trajectories
            full_strides = modeller.engine.full_strides

            frame_state_list = {n: [] for n in range(n_states)}
            for nn, dt in enumerate(data['clustering']['dtrajs']):
                for mm, state in enumerate(dt):
                    # if there is a full traj with existing frame, use it
                    if any([(mm * used_stride) % stride == 0 for stride in full_strides]):
                        frame_state_list[state].append((nn, mm * used_stride))

            c = data['msm']['C']
            q = 1.0 / np.sum(c, axis=1)

            # remove states that do not have at least one frame
            for k in range(n_states):
                if len(frame_state_list[k]) == 0:
                    q[k] = 0.0

            # and normalize the remaining ones
            q /= np.sum(q)

            state_picks = np.random.choice(np.arange(len(q)), size=n_pick, p=q)

            filelist = data['input']['trajectories']

            picks = [
                frame_state_list[state][np.random.randint(0, len(frame_state_list[state]))]
                for state in state_picks
                ]

            return [filelist[pick[0]][pick[1]] for pick in picks]

        elif len(self.trajectories) > 0:
            # otherwise pick random
            return [
                self.trajectories.pick().pick() for _ in range(n_pick)]
        else:
            return []

    def new_ml_trajectory(self, engine, length, number):
        """
        Find trajectories that have initial points picked by inverse eq dist

        Parameters
        ----------
        engine : `Engine`
            the engine to be used
        length : int
            length of the trajectories returned
        number : int
            number of trajectories returned

        Returns
        -------
        list of `Trajectory`
            the list of `Trajectory` objects with initial frames chosen using
            :meth:`find_ml_next_frame`

        See Also
        --------
        :meth:`find_ml_next_frame`

        """
        return [self.new_trajectory(frame, length, engine) for frame in
                self.find_ml_next_frame(number)]

    def events_done(self):
        """
        Check if all events are done

        Returns
        -------
        bool
            True if all events are done
        """
        return len(self._events) == 0

    def add_event(self, event):
        """
        Attach an event to the project

        These events will not be stored and only run in the current python
        session. These are the parts responsible to create tasks given
        certain conditions.

        Parameters
        ----------
        event : `Event` or generator
            the event to be added or a generator function that is then
            converted to an `ExecutionPlan`

        Returns
        -------
        `Event`
            the actual event used

        """
        if isinstance(event, (tuple, list)):
            return map(self._events.append, event)

        if isinstance(event, types.GeneratorType):
            event = ExecutionPlan(event)

        self._events.append(event)

        logger.info('Events added. Remaining %d' % len(self._events))

        self.trigger()
        return event

    def trigger(self):
        """
        Trigger a check of state changes that leads to task execution

        This needs to be called regularly to advance the simulation. If not,
        certain checks for state change will not be called and no new tasks
        will be generated.

        """
        with self._lock:
            found_iteration = 50  # max iterations for safety
            while found_iteration > 0:
                found_new_events = False
                for event in list(self._events):
                    if event:
                        new_events = event.trigger(self)

                        if new_events:
                            found_new_events = True

                    if not event:
                        # event is finished, clean up
                        idx = self._events.index(event)

                        # todo: wait for completion
                        del self._events[idx]
                        logger.info('Event finished! Remaining %d' % len(self._events))

                if found_new_events:
                    # if new events or tasks we should re-trigger
                    found_iteration -= 1
                else:
                    found_iteration = 0

            # check worker status and mark as dead if not responding for long times
            now = time.time()
            for w in self.workers:
                if w.state not in ['dead', 'down'] and now - w.seen > self._worker_dead_time:
                    # make sure it will end and not finish any jobs, just in case
                    w.command = 'kill'

                    # and mark it dead
                    w.state = 'dead'

                    # search for abandoned tasks and do something with them
                    if self._set_task_state_from_dead_workers:
                        for t in self.tasks:
                            if t.worker == w and t.state in ['queued', 'running']:
                                t.state = self._set_task_state_from_dead_workers

                    w.current = None

    def run(self):
        """
        Starts observing events in the project

        This is still somehow experimental and will call a background thread to
        call :meth:`Project.trigger` in regular intervals. Make sure to call
        :meth:`Project.stop`
        before you quit the notebook session or exit. Otherwise there might
        be a job in the background left (not confirmed but possible!)

        """
        if not self._event_timer:
            self._stop_event = threading.Event()
            self._event_timer = self.EventTriggerTimer(self._stop_event, self)
            self._event_timer.start()

    def stop(self):
        """
        Stop observing events

        """
        if self._event_timer:
            self._stop_event.set()
            self._event_timer = None
            self._stop_event = None

    def wait_until(self, condition):
        """
        Block until the given condition evaluates to true

        Parameters
        ----------
        condition : callable
            function that is called in regular intervals. If it evaluates to
            True the function returns

        """
        while not condition():
            self.trigger()
            time.sleep(5.0)

    class EventTriggerTimer(threading.Thread):
        """
        A special thread to call the project trigger mechanism

        """
        def __init__(self, event, project):

            super(Project.EventTriggerTimer, self).__init__()
            self.stopped = event
            self.project = project

        def run(self):
            while not self.stopped.wait(5.0):
                self.project.trigger()


class NTrajectories(Condition):
    """
    Condition that triggers if a resource has at least n trajectories present

    """
    def __init__(self, project, number):
        super(NTrajectories, self).__init__()
        self.project = project
        self.number = number

    def check(self):
        return len(self.project.trajectories) >= self.number

    def __str__(self):
        return '#files[%d] >= %d' % (len(self.project.trajectories), self.number)

    def __add__(self, other):
        if isinstance(other, int):
            return NTrajectories(self.project, self.number + other)

        return NotImplemented


class NModels(Condition):
    """
     Condition that triggers if a resource has at least n models present

     """

    def __init__(self, project, number):
        super(NModels, self).__init__()
        self.project = project
        self.number = number

    def check(self):
        return len(self.project.models) >= self.number

    def __str__(self):
        return '#models[%d] >= %d' % (len(self.project.models), self.number)

    def __add__(self, other):
        if isinstance(other, int):
            return NModels(self.project, self.number + other)

        return NotImplemented
