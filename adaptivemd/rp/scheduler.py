import time

from adaptivemd.scheduler import Scheduler
from adaptivemd.reducer import DictFilterParser, StrFilterParser, BashParser, StageParser, \
    StageInParser, PrefixParser

from radical import pilot as rp


class RPScheduler(Scheduler):
    def __init__(self, resource, queue=None, runtime=240, cores=1,
                 rp_resource=None):
        """

        Parameters
        ----------
        resource : `Resource`
            a `Resource` where this scheduler works on
        queue : str
            the name of the queue to be used for pilot creation
        runtime : int
            max runtime in minutes for the created pilot
        cores
            number of used cores to be used in the created pilot
        rp_resource : str
            the resource name for the pilot. If set it will override the default from the
            resource
        """

        super(RPScheduler, self).__init__(resource, queue, runtime, cores)

        if rp_resource is None:
            rp_resource = resource.resource

        self.rp_resource = rp_resource

        self.unit_manager = None
        self.pilot = None

        self.units = dict()

    @property
    def desc(self):
        resource = self.resource
        pd = {
            'resource': self.rp_resource,
            'runtime': self.runtime,
            'exit_on_error': resource.exit_on_error,
            'project': resource.project,
            'queue': self.queue,
            'access_schema': resource.access_schema,
            'cores': self.cores
        }
        return rp.ComputePilotDescription(pd)

    @property
    def staging_area_location(self):
        return 'sandbox:///' + self.folder_name + '/staging_area'

    def __getitem__(self, item):
        return self.generators.get(item)

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

        self.exit()

        return fail

    def enter(self, project=None):
        if project is not None:
            self.project = project

        project = self.project

        # just in case the user did not open a session yet, we do it now
        if project.session is None:
            project.open_rp()

        self.unit_manager = rp.UnitManager(session=project.session)

        # register this cluster with the session for later cleanup
        self.project.schedulers.add(self)

        self.pilot = self.project.pilot_manager.submit_pilots(self.desc)

        self.unit_manager.add_pilots(self.pilot)
        self.unit_manager.register_callback(self.unit_callback)

        self._folder_name = '%s-%s' % (
            project.session._uid, self.pilot._uid)

        self.stage_generators()

    def exit(self):
        self.shut_down(False)

    def stage_generators(self):
        reducer = DictFilterParser() >> StageInParser()
        for g in self.generators:
            self.stage_in(reducer(self, g.stage_in))

    def stage_in(self, staging):
        self.pilot.stage_in(staging)

    def task_to_cud(self, task):
        cud = rp.ComputeUnitDescription()

        copies = [
            'executable', 'arguments',
            'environment', 'cores', 'mpi', 'stdout',
            'stderr', 'kernel', 'name', 'restartable', 'cleanup']

        for name in copies:
            if hasattr(task, name):
                setattr(cud, name, getattr(task, name))

        cud.cores = cud.cores

        # create staging

        main_parser = PrefixParser() >> BashParser() >> StageParser()
        reducer = DictFilterParser() >> main_parser

        cud.input_staging = reducer(self, task.input_staging)
        cud.output_staging = reducer(self, task.output_staging)

        reducer = StrFilterParser() >> main_parser

        cud.pre_exec = reducer(self, task.pre_exec)
        cud.post_exec = reducer(self, task.post_exec)

        return cud

    def unit_callback(self, unit, state):
        """
        The callback for simulation units

        This will update the list of finished jobs and existing trajectories

        Parameters
        ----------
        unit : `ComputeUnit`
            the `radical.pilot.ComputeUnit` that had its state changed
        state : str
            the new state

        """

        if unit is None:
            return

        task = self.tasks.get(unit.uid)

        if not task:
            return

        # fire `change` events for task. Usually not used
        task.fire('change', self)

        # not good. Something went wrong
        if state in [rp.FAILED, rp.CANCELED]:
            self.remove_task(task)
            task.fire('fail', self)

            # check events
            self.trigger()

        elif state in [rp.DONE]:
            self.remove_task(task)
            task.fire('success', self)

            # check events
            self.trigger()

    def remove_task(self, task):
        unit = self.units[task]
        del self.units[task]
        del self.tasks[unit.uid]
        print 'Task removed. Remaining', len(self.tasks)

    def submit(self, submission):
        """
        Submit a task in form of an event, a task or an taskable object

        Parameters
        ----------
        submission : (list of) [`Task` or `object` or `Event`]

        Returns
        -------
        list of `Task`
            the list of tasks actually executed after looking at all objects

        """
        tasks = self._to_tasks(submission)

        if tasks:
            cuds = map(
                lambda x: self.task_to_cud(x >> self.wrapper),
                tasks
            )

            map(lambda x: x.fire('submit', self), tasks)

            units = self.unit_manager.submit_units(cuds)
            for unit, task in zip(units, tasks):
                self.tasks[unit.uid] = task
                self.units[task] = unit

        events = self._to_events(submission)
        map(self._events.append, events)

        return tasks

    def add_event(self, event):
        if isinstance(event, (tuple, list)):
            map(self._events.append, event)
        else:
            self._events.append(event)

        self.trigger()

        return event

    def trigger(self):
        """
        Trigger a check of state changes that leads to task execution

        """
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

            if found_new_events:
                # if new events or tasks we should retrigger
                found_iteration -= 1
            else:
                found_iteration = 0

        # delegate to project level
        self.project.trigger()

    def shut_down(self, wait_to_finish=True):
        """
        Do a controlled shutdown. Cancel all units and wait until they finish.

        Parameters
        ----------
        wait_to_finish : bool
            if `True` default the function will block until all tasks report
            finish

        """
        if not self._finished:
            self._stop_signal = True
            self._shutting_down = True

            # cancel all we can
            for task, unit in self.units.items():
                try:
                    self.unit_manager.cancel_units(unit.uid)
                    del self.tasks[unit.uid]
                    del self.units[task]

                except rp.exceptions.IncorrectState:
                    pass

            # wait for the rest to finish
            if wait_to_finish:
                self.unit_manager.wait_units()

                self.tasks = {}
                self.units = {}

            if self.project is not None:
                self.project.schedulers.remove(self)

            self._shutting_down = False
            self._finished = True

    def wait(self):
        """
        Wait until no more units are running and hence no more state changes

        """

        while not self._stop_signal \
                and len(self.units) > 0:
            time.sleep(2.0)

    def cancel_events(self):
        """
        Remove all pending events and stop them from further task execution

        """
        for ev in self._events:
            ev.cancel()

        self._events = []

    def replace_prefix(self, path):
        path = path.replace('staging://', '../staging_area')

        # the rp sandbox://
        path = path.replace('sandbox://', '../..')

        # the main remote shared FS
        path = path.replace('shared://', '../../..')
        path = path.replace('worker://', '')
        path = path.replace('file://', '')

        return path
