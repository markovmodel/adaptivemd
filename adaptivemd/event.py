import types

from condition import Condition
from itertools import chain
from task import Task


class Event(object):
    """
    Class describing the condition and function execution of some code
    """

    _skip_done_conditions = True
    _wait_for_completion = True

    def __init__(self, when=None):
        self._on = None
        self._until = None

        self._finish_conditions = []
        self._active_tasks = []
        self._generator = None
        self._current_when = None
        self._current_iter = None

        if when is not None:
            self.on(when)

    def on(self, when):
        """
        Specify a list of conditions when the event is to be executed

        Parameters
        ----------
        when : (list of) callable -> bool
            a condition (a function the returns a bool) that is tested for
            and if it is true (once trigger is called) the event will
            be executed and the next condition will be waited for.

        Returns
        -------
        self
            return the object itself for chaining

        """
        self._on = when
        if hasattr(self._on, '__iter__'):
            # there are multiple conditions so pick first
            self._current_iter = iter(self._on)
        else:
            self._current_iter = iter([self._on])

        self._advance()

        return self

    def _advance(self):
        try:
            # there are multiple conditions so pick first
            self._current_when = next(self._current_iter)
        except StopIteration:
            self._current_when = None

    def _update_task_list(self):
        self._active_tasks = filter(lambda x: not x.is_done(),
                                    self._active_tasks)

        self._finish_conditions = filter(lambda x: x(), self._finish_conditions)

    @property
    def active_tasks(self):
        self._update_task_list()
        return self._active_tasks

    @property
    def has_running_tasks(self):
        self._update_task_list()
        return len(self._finish_conditions) > 0
        # return len(self._active_tasks) > 0

    def __nonzero__(self):
        self._update_task_list()
        return self._current_when is not None or self.has_running_tasks

    def _generate(self, scheduler):
        if self._generator is not None:
            # todo: this should be cleaner and not guess the number of args
            try:
                return self._generator(scheduler)
            except TypeError:
                return self._generator()
        else:
            return []

    def __call__(self, scheduler):
        generated = self._generate(scheduler)
        tasks = scheduler.submit(generated)

        for t in tasks:
            if isinstance(t, Task):
                self._active_tasks.append(t)
                self._finish_conditions.append(t.is_done)

        # self._active_tasks.extend(tasks)

        return generated

    def trigger(self, scheduler):
        """
        Test conditions and trigger execution if fulfilled

        Parameters
        ----------
        scheduler : `Scheduler`
            the scheduler which will handle submission of tasks if desired

        Returns
        -------
        list of `Task`
            a list of task that should be run
        """
        if self:
            if not self.has_running_tasks or not self._wait_for_completion:
                if self._until is not None and self._until():
                    self._current_when = None

                if self._current_when and self._current_when():
                    tasks = self(scheduler)

                    self._advance()
                    if self._skip_done_conditions:
                        while self._current_when is not None and \
                                self._current_when():
                            self._advance()

                    return tasks

        return []

    def __str__(self):
        return '%s(%s, %s[%s])' % (
            'active' if self else '------',
            self.__class__.__name__,
            str(self._current_when),
            str(self._current_when()) if self._current_when else 'None',
        )

    def repeat(self, times=None):
        """
        Set the event iter to restart if its tasks are finished

        Notes
        -----
        This overrides potential multiple trigger events and just repeats when
        finished until the stop condition is met

        Returns
        -------
        self

        """
        if times is None:
            self._current_iter = chain(
                self._current_iter,
                (TasksFinished(self) for _ in iter(int, 1)))
        else:
            self._current_iter = chain(
                self._current_iter,
                (TasksFinished(self) for _ in range(times)))

        return self

    def until(self, repeat):
        """
        Set the event iter to restart if its tasks are finished

        Notes
        -----
        This overrides potential multiple trigger events and just repeats when
        finished until the stop condition is met

        Returns
        -------
        self
        """
        self._until = repeat

        return self

    def do(self, generator):
        """
        Set the task generator to be used once a condition is met

        Parameters
        ----------
        generator : function -> list of `Task`

        Returns
        -------
        self
        """
        self._generator = generator
        return self

    def cancel(self):
        """
        Stop execution of future events

        """
        self._current_when = None

    @property
    def on_done(self):
        """
        Return a `Condition` that is True once the event is finished

        Returns
        -------

        """
        return TasksFinished(self)


class FunctionalEvent(Event):
    """
    An Event to wrap a python function

    The function is executed on start and interrupted if you use `yield {condition to continue}`

    To make writing of asynchronous code easy you can use this wrapper class. Usually you
    start by opening a scheduler that you submit tasks to. Then submit a first task or
    yield a condition to wait for. Once this is met the code will continue to execute and
    you can submit more tasks until finally you will close the scheduler

    Attributes
    ----------
    generator : generator
        the function (generator) to be used

    """
    def __init__(self, generator):
        super(FunctionalEvent, self).__init__()

        if not isinstance(generator, types.GeneratorType):
            generator = generator()

        assert isinstance(generator, types.GeneratorType)

        self.do(generator)
        self._running = True

    def _update_conditions(self):
        self._finish_conditions = filter(
            lambda x: not x(), self._finish_conditions)

    def __call__(self, scheduler):
        if self._running:
            try:
                conditions = next(self._generator)
                if conditions is not None:
                    if isinstance(conditions, (tuple, list)):
                        self._finish_conditions.extend(conditions)
                    else:
                        self._finish_conditions.append(conditions)
                self._update_conditions()
            except StopIteration:
                self._running = False

    def trigger(self, scheduler):
        if self:
            if self._until is not None and self._until():
                self._running = False
            else:
                self._update_conditions()
                while self._running and len(self._finish_conditions) == 0:
                    self(scheduler)
                    self._update_conditions()

    def __nonzero__(self):
        return self._running


class TasksFinished(Condition):
    """
    Condition to represent the completion of an `Event`
    """
    def __init__(self, event):
        super(TasksFinished, self).__init__()
        self.event = event

    def check(self):
        return not bool(self.event)


class StopEvent(Event):
    """
    Event that represents the termination of the used scheduler
    """
    def __call__(self, scheduler):
        return StopIteration
