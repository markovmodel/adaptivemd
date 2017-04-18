import types


class ExecutionPlan(object):
    """
    An wrap to turn python function into asynchronous execution

    The function is executed on start and interrupted if you use
    ``yield {(list of )condition to continue}``

    To make writing of asynchronous code easy you can use this wrapper class.
    Usually you start by opening a scheduler that you submit tasks to. Then
    submit a first task or yield a condition to wait for. Once this is met the
    code will continue to execute and you can submit more tasks until finally
    you will close the scheduler

    """
    def __init__(self, generator):
        """
        Parameters
        ----------
        generator : function
            the function (generator) to be used

        """
        super(ExecutionPlan, self).__init__()

        if not isinstance(generator, types.GeneratorType):
            generator = generator()

        assert isinstance(generator, types.GeneratorType)

        self._generator = generator
        self._running = True
        self._finish_conditions = []

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
            self._update_conditions()
            while self._running and len(self._finish_conditions) == 0:
                self(scheduler)
                self._update_conditions()

    def __nonzero__(self):
        return self._running

    def __str__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            'active' if self else '------'
        )

    @property
    def on_done(self):
        """
        Return a `Condition` that is True once the event is finished

        Returns
        -------

        """
        return lambda: not bool(self)