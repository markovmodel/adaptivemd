from event import Event
from file import Location
from mongodb import ObjectJSON
from task import Task, DummyTask


class Scheduler(object):
    """
    Class to handle task execution on a resource

    Notes
    -----
    In RP this would correspond to a Pilot with a UnitManager

    Attributes
    ----------
    project : `Project`
        a back reference to the project that uses this scheduler
    tasks : dict uid : `Task`
        dict that references all running task by the associated CU.uid
    wrapper : `Task`
        a wrapping task that contains additional commands to be executed
        around each task running on that scheduler. It usually contains
        adding certain paths, etc.
    """

    def __init__(self, resource, queue=None, runtime=240, cores=1):
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
        """

        self.resource = resource
        self.queue = queue
        self.runtime = runtime
        self.cores = cores

        self.project = None

        self.tasks = dict()

        self.auto_submit_dependencies = True

        self._generator_list = []

        self._events = []
        self._stop_signal = False
        self._shutting_down = False
        self._finished = False

        self.wrapper = DummyTask()

        self._folder_name = None

        self.simplifier = ObjectJSON()

    @property
    def staging_area_location(self):
        return 'sandbox:///' + self.folder_name + '/staging_area'

    @property
    def generators(self):
        if self.project:
            return self.project.generators
        else:
            return []

    @property
    def file_generators(self):
        if self.project:
            return self.project.file_generators
        else:
            return {}

    @property
    def folder_name(self):
        return self._folder_name

    def get_path(self, f):
        """
        Convert the location in a `Location` object to a real path used by the scheduler

        Parameters
        ----------
        file : `Location`
            the location object

        Returns
        -------
        str
            a real file path
        """
        return self.replace_prefix(f.url)

    def in_staging_area(self, url):
        pass

    def unroll_staging_path(self, location):
        if location.drive == 'staging':
            location.location = self.staging_area_location + location.path

    def has(self, name):
        if isinstance(name, (list, tuple)):
            self._generator_list.extend(name)
        else:
            self._generator_list.append(name)

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

    def __call__(self, submission):
        return self.submit(submission)

    @property
    def is_idle(self):
        return len(self.tasks) == 0

    def exit(self):
        self.shut_down(False)

    def stage_generators(self):
        pass

    def stage_in(self, staging):
        pass

    def flatten_location(self, obj):
        if isinstance(obj, Location):
            return self.replace_prefix(obj.url)
        elif isinstance(obj, list):
            return map(self.flatten_location, obj)
        elif isinstance(obj, dict):
            return {
                self.flatten_location(key): self.flatten_location(value)
                for key, value in obj.iteritems()
            }
        elif isinstance(obj, tuple):
            return tuple(map(self.flatten_location, obj))
        else:
            return obj

    def remove_task(self, task):
        pass

    def _to_tasks(self, submission):

        if isinstance(submission, (tuple, list)):
            return sum(map(self._to_tasks, submission), [])

        elif isinstance(submission, Task):
            if submission in self.tasks.values() or submission.is_done():
                return []

            if submission.ready:
                return [submission]
            else:
                if self.auto_submit_dependencies:
                    return self._to_tasks(submission.dependencies)
                else:
                    return []
        else:
            for cls, gen in self.file_generators.items():
                if isinstance(submission, cls):
                    return self._to_tasks(gen(submission))

            return []

    def _to_events(self, submission):
        if isinstance(submission, (tuple, list)):
            return sum(map(self._to_events, submission), [])

        elif isinstance(submission, Event):
            return [submission]
        else:
            return []

    def submit(self, submission):
        """
        Submit a task in form of an event, a task or an task-like object

        Parameters
        ----------
        submission : (list of) [`Task` or `object` or `Event`]

        Returns
        -------
        list of `Task`
            the list of tasks actually executed after looking at all objects

        """
        return self._to_tasks(submission)

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
            self._finished = True

    def on(self, condition):
        """
        Shortcut for creation and appending of a new Event

        Parameters
        ----------
        condition : `Condition`

        Returns
        -------
        `Event`

        """
        ev = Event(condition)
        self._events.append(ev)
        return ev

    def wait(self):
        """
        Wait until no more units are running and hence no more state changes

        """

        pass

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
