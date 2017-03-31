.. _worker:

.. currentmodule:: adaptivemd

Workers
=======

:class:`adaptive.Worker`s are the main execution units of your :class:`adaptive.Task` instances.
While the :class:`adaptive.Task` object contains specifics about what you want
to happen, like create a trajectory with this length, it does not know anything
about where to run it and how to achieve the goal there. The :class:`adaptive.Task`
definition is concrete but it misses knowlegde that only the actual
:class:`adaptive.Worker` that executes it has. Things like the actual working
directory, (you do not want to interfere with other workers), how to copy
a file from A to B, etc...

There are two ways to use a :class:`adaptive.Worker`,

1. a manual way in a script, or
2. through a stand-alone bash command. That will run a python script which
   creates a Worker with some options and just runs it until it is shut down.

You will be mostly using the 2. way since it is much simpler and you will
typically submit it to the queue and then it will listen in the DB for task to
be run in regular intervals.


How does it work
""""""""""""""""

Technically a worker gets a task to execute (the task of picking a task from the
DB is not solved by the worker!). Then

1. A new worker directory is created named according to the task
2. It will convert the given task into a bash script (this might involve already
   copying files from the DB to some folders since this is something that is
   not handled in a bash script)
3. The bash script is executed within the current working directory
4. Once it is finished and succeeded the outputs are stored and created files
   are registered as being existent now.
5. A Callback is run, if the task had one


Communication
"""""""""""""

The actual worker will run somewhere on the HPC or as a separate process on your
local machine. In both cases the Worker instance will not be present in your
execution script or notebook. Hence changes or function you call in your notebook
will have no effect to the worker running somewhere else.

Still, any worker that you create through the ``adaptivemdworker`` script will
be stored in the project, so its settings are visible to anyone with access
you your project DB.

Using the BD, you have a way to connect to the worker. You can set a specaicl
property which is checked by the running worker in regular intervals and if it
takes special values the Worker will act. You could try

.. code-block::python

    worker = project.workers.one  # get any one worker
    print worker.state  # should be `running`
    worker.execute('shutdown')  # will send the `shutdown` command
    time.sleep(5)  # wait 5 seconds
    print worker.state  # should be `down`

The other typical thing that is of interest is the status of the worker

.. code-block::python

    project.trigger()  # force the project to update
    for w in project.workers:
        if w.state == 'running':
            print '[%s:%s] %s:%s' % (w.state, DT(w.seen).time, w.hostname, w.cwd)


Dead workers
""""""""""""

This is bad and should not happen, but it can. When a worker dies it does not
mean that its execution thread died. The bash script will be run in another
thread that is monitored (and should also die if the worker is killed).

Now the worker stalls and stops accepting tasks, etc. What happens?

The worker will continuously send a heartbeat to the DB, which is just a
current timestamp. It does this every 10 seconds. You can simply check this by

.. code-block::python

    project.trigger()  # force the project to update
    for w in project.workers:
        if w.state == 'running':
            print '[%s] last alive %s ago' % (w.state, DT(time.time() - w.seen).length)

with the ``.seen`` property.

If it is supposed to write it every 10 seconds and it does not do that for a
minute we get suspicious. When calling ``project.trigger()`` which will also
look for open events to be run, the project also checks, if all workers are
still alive -- where alive means that there last alive time is > 60s.

So, if a worker is considered dead, it is sends the ``kill`` command just to make
sure that it will be dead when we will consider it being so and not secretly
keep on working. There would be no problem, if it would sill run correctly but
if it really had failed we want to retry the failed job.

Next, the current task is considered failed and will be restarted. This means
just to set the ``task.state`` to ``created``. And another worker that is
responding can pick it up. This task will overwrite all files that the failed
task would have generated and so we keep consistent in the database.

RUN ``adaptivemdworker``
------------------------

the tool ``adaptivemdworker`` takes some options

    usage: adaptivemdworker [-h] [-t [WALLTIME]] [-d [MONGO_DB_PATH]]
                            [-g [GENERATORS]] [-w [WRAPPERS]] [-l] [-v] [-a]
                            [--sheep] [-s [SLEEP]] [--heartbeat [HEARTBEAT]]
                            project_name

    Run an AdaptiveMD worker

    positional arguments:
      project_name          project name the worker should attach to

    optional arguments:
      -h, --help            show this help message and exit
      -t [WALLTIME], --walltime [WALLTIME]
                            minutes until the worker shuts down. If 0 (default) it
                            will run indefinitely
      -d [MONGO_DB_PATH], --mongodb [MONGO_DB_PATH]
                            the mongodb url to the db server
      -g [GENERATORS], --generators [GENERATORS]
                            a comma separated list of generator names used to
                            dispatch the tasks. the worker will only respond to
                            tasks from generators whose names match one of the
                            names in the given list. Example: --generators=openmm
                            will only run scripts from generators named `openmm`
      -w [WRAPPERS], --wrappers [WRAPPERS]
                            a comma separated list of simple function call to the
                            resource. This can be used to add e.g. CUDA support
                            for specific workers. Example:
                            --wrappers=add_path("something"),add_cuda_module()
      -l, --local           if true then the DB is set to the default local port
      -v, --verbose         if true then stdout and stderr of subprocesses will be
                            rerouted. Use for debugging.
      -a, --allegro         if true then the DB is set to the default allegro
                            setting
      --sheep               if true then the DB is set to the default sheep
                            setting
      -s [SLEEP], --sleep [SLEEP]
                            polling interval for new jobs in seconds. Default is 2
                            seconds. Increase to get less traffic on the DB
      --heartbeat [HEARTBEAT]
                            heartbeat interval in seconds. Default is 10 seconds.

Examples
""""""""

Run using the local DB setting ``mongodb://localhost:27019`` for ``my_project``

    adaptivemdworker -l my_project

Classes
-------

.. autosummary::
    :toctree: api/generated/

    Worker
