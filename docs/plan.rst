.. _plan:

.. currentmodule:: adaptivemd


Execution Plans
===============

You are free to conduct your simulations from a notebook but normally
you will use a script. The main point about adaptivity is to make
decision about tasks along the way.

We want to first look into a way to run python code asynchroneously in
the project. For this, we write a function that should be executed.
Inside you will create tasks and submit them.

If the function should pause, use ``yield`` as if you would ``return``
and exit the function. ``Yield`` will allow you to continue at this

.. code:: python

    yield {condition_to_continue}

This will interrupt your script until the function you return will
return ``True`` when called. An example

.. code:: python

    def strategy(loops=10, trajs_per_loop=4, length=100):
        for loop in range(loops):
            # submit some trajectory tasks
            trajectories = project.new_ml_trajectory(length, trajs_per_loop)
            tasks = map(engine.task_run_trajectory, trajectories)
            project.queue(tasks)

            # continue if ALL of the tasks are done (can be failed)
            yield [task.is_done for task in tasks]

            # submit a model job
            task = modeller.execute(list(project.trajectories))
            project.queue(task)

            # when it is done do next loop
            yield task.is_done

and add the event to the project (these cannot be stored yet!)

.. code:: python

    project.add_event(strategy(loops=2))




.. parsed-literal::

    <adaptivemd.event.FunctionalEvent at 0x10d615050>



What is missing now? The adding of the event triggered the first part of
the code. But to recheck if we should continue needs to be done
manually.

    RP has threads in the background and these can call the trigger
    whenever something changed or finished.

Still that is no problem, we can do that easily and watch what is
happening

Let's see how our project is growing. TODO: Add threading.Timer to auto
trigger.

.. code:: python

    import time
    from IPython.display import clear_output

.. code:: python

    try:
        while project._events:
            clear_output(wait=True)
            print '# of files  %8d : %s' % (len(project.trajectories), '#' * len(project.trajectories))
            print '# of models %8d : %s' % (len(project.models), '#' * len(project.models))
            sys.stdout.flush()
            time.sleep(2)
            project.trigger()

    except KeyboardInterrupt:
        pass


.. parsed-literal::

    # of files        74 : ##########################################################################
    # of models       33 : #################################


Let's do another round with more loops

.. code:: python

    project.add_event(strategy(loops=2))




.. parsed-literal::

    <adaptivemd.event.FunctionalEvent at 0x10d633850>



And some analysis (might have better functions for that)

.. code:: python

    # find, which frames from which trajectories have been chosen
    trajs = project.trajectories
    q = {}
    ins = {}
    for f in trajs:
        source = f.frame if isinstance(f.frame, File) else f.frame.trajectory
        ind = 0 if isinstance(f.frame, File) else f.frame.index
        ins[source] = ins.get(source, []) + [ind]

    for a,b in ins.iteritems():
        print a.short, ':', b


.. parsed-literal::

    file://{}/alanine.pdb : [0, 0, 0]
    sandbox:///{}/00000005/ : [95, 92, 67, 92]
    sandbox:///{}/00000007/ : [11]
    sandbox:///{}/00000011/ : [55]
    sandbox:///{}/00000000/ : [28, 89, 72]
    sandbox:///{}/00000002/ : [106]
    sandbox:///{}/00000004/ : [31, 25, 60]


Event
~~~~~

And do this with multiple events in parallel.

.. code:: python

    def strategy2():
        for loop in range(10):
            num = len(project.trajectories)
            task = modeller.execute(list(project.trajectories))
            project.queue(task)
            yield task.is_done
            # continue only when there are at least 2 more trajectories
            yield project.on_ntraj(num + 2)

.. code:: python

    project.add_event(strategy(loops=10, trajs_per_loop=2))
    project.add_event(strategy2())




.. parsed-literal::

    <adaptivemd.event.FunctionalEvent at 0x107744c90>



And now wait until all events are finished.

.. code:: python

    project.wait_until(project.events_done)


Classes
-------

.. autosummary::
    :toctree: api/generated/

    ExecutionPlan