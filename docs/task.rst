.. _task:

.. currentmodule:: adaptivemd

Task
====

A :class:`Task` is in essence a bash script-like description of what should be
executed by the worker. It has details about files to be linked to the
working directory, bash commands to be executed and some meta
information about what should happen in case we succeed or fail.


The execution structure
^^^^^^^^^^^^^^^^^^^^^^^

Let's first explain briefly how a task is executed and what its
components are. This was originally build so that it is compatible with
radical.pilot and still is. So, if you are familiar with it, all of the
following information should sould very familiar.

A task is executed from within a unique directory that only exists for
this particular task. These are located in ``adaptivemd/workers/`` and
look like

::

    worker.0x5dcccd05097611e7829b000000000072L/

the long number is a hex representation of the UUID of the task. Just if
you are curious type

::

    print hex(my_task.__uuid__)

Then we change directory to this folder write a ``running.sh`` bash
script and execute it. This script is created from the task definition
and also depends on your resource setting (which basically only contain
the path to the workers directory, etc)

The script is divided into 1 or 3 parts depending on which ``Task``
class you use. The main ``Task`` uses a single list of commands, while
``PrePostTask`` has the following structure

1. **Pre-Exec**: Things to happen before the main command (optional)

2. **Main**: the main commands are executed

3. **Post-Exec**: Things to happen after the main command (optional)

Okay, lots of theory, now some real code for running a task that
generated a trajectory

.. code:: python

    task = engine.task_run_trajectory(project.new_trajectory(pdb_file, 100))

.. code:: python

    task.script




.. parsed-literal::

    [Link('staging:///alanine.pdb' > 'worker://initial.pdb),
     Link('staging:///system.xml' > 'worker://system.xml),
     Link('staging:///integrator.xml' > 'worker://integrator.xml),
     Link('staging:///openmmrun.py' > 'worker://openmmrun.py),
     Touch('worker://traj/'),
     'python openmmrun.py -r --report-interval 1 -p CPU --store-interval 1 -t worker://initial.pdb --length 100 worker://traj/',
     Move('worker://traj/' > 'sandbox:///{}/00000076/)]



We are linking a lot of files to the worker directory and change the
name for the .pdb in the process. Then call the actual ``python`` script
that runs openmm. And finally move the ``output.dcd`` and the restart
file back tp the trajectory folder.

There is a way to list lot's of things about tasks and we will use it a
lot to see our modifications.

.. code:: python

    print task.description


.. parsed-literal::

    Task: TrajectoryGenerationTask(OpenMMEngine) [created]

    Sources
    - staging:///integrator.xml
    - staging:///alanine.pdb
    - staging:///openmmrun.py
    - staging:///system.xml
    Targets
    - sandbox:///{}/00000076/
    Modified

    <pretask>
    Link('staging:///alanine.pdb' > 'worker://initial.pdb)
    Link('staging:///system.xml' > 'worker://system.xml)
    Link('staging:///integrator.xml' > 'worker://integrator.xml)
    Link('staging:///openmmrun.py' > 'worker://openmmrun.py)
    Touch('worker://traj/')
    python openmmrun.py -r --report-interval 1 -p CPU --store-interval 1 -t worker://initial.pdb --length 100 worker://traj/
    Move('worker://traj/' > 'sandbox:///{}/00000076/)
    <posttask>


Modify a task
~~~~~~~~~~~~~

As long as a task is not saved and hence placed in the queue, it can be
altered in any way. All of the 3 / 5 phases can be changed separately.
You can add things to the staging phases or bash phases or change the
command. So, let's do that now

Add a bash line
^^^^^^^^^^^^^^^

First, a ``Task`` is very similar to a list of bash commands and you can
simply append (or prepend) a command. A text line will be interpreted as
a bash command.

.. code:: python

    task.append('echo "This new line is pointless"')

.. code:: python

    print task.description


.. parsed-literal::

    Task: TrajectoryGenerationTask(OpenMMEngine) [created]

    Sources
    - staging:///integrator.xml
    - staging:///alanine.pdb
    - staging:///openmmrun.py
    - staging:///system.xml
    Targets
    - sandbox:///{}/00000076/
    Modified

    <pretask>
    Link('staging:///alanine.pdb' > 'worker://initial.pdb)
    Link('staging:///system.xml' > 'worker://system.xml)
    Link('staging:///integrator.xml' > 'worker://integrator.xml)
    Link('staging:///openmmrun.py' > 'worker://openmmrun.py)
    Touch('worker://traj/')
    python openmmrun.py -r --report-interval 1 -p CPU --store-interval 1 -t worker://initial.pdb --length 100 worker://traj/
    Move('worker://traj/' > 'sandbox:///{}/00000076/)
    echo "This new line is pointless"
    <posttask>


As expected this line was added to the end of the script.

Add staging actions
^^^^^^^^^^^^^^^^^^^

To set staging is more difficult. The reason is, that you normally have
no idea where files are located and hence writing a copy or move is
impossible. This is why the staging commands are not bash lines but
objects that hold information about the actual file transaction to be
done. There are some task methods that help you move files but also
files itself can generate this commands for you.

Let's move one trajectory (directory) around a little more as an example

.. code:: python

    traj = project.trajectories.one

.. code:: python

    transaction = traj.copy()
    print transaction


.. parsed-literal::

    Copy('sandbox:///{}/00000010/' > 'worker://)


This looks like in the script. The default for a copy is to move a file
or folder to the worker directory under the same name, but you can give
it another name/location if you use that as an argument. Note that since
trajectories are a directory you need to give a directory name (which
end in a ``/``)

.. code:: python

    transaction = traj.copy('new_traj/')
    print transaction


.. parsed-literal::

    Copy('sandbox:///{}/00000010/' > 'worker://new_traj/)


If you want to move it not to the worker directory you have to specify
the location and you can do so with the prefixes (``shared://``,
``sandbox://``, ``staging://`` as explained in the previous examples)

.. code:: python

    transaction = traj.copy('staging:///cached_trajs/')
    print transaction


.. parsed-literal::

    Copy('sandbox:///{}/00000010/' > 'staging:///cached_trajs/)


Besides ``.copy`` you can also ``.move`` or ``.link`` files.

.. code:: python

    transaction = pdb_file.copy('staging:///delete.pdb')
    print transaction
    transaction = pdb_file.move('staging:///delete.pdb')
    print transaction
    transaction = pdb_file.link('staging:///delete.pdb')
    print transaction


.. parsed-literal::

    Copy('file://{}/alanine.pdb' > 'staging:///delete.pdb)
    Move('file://{}/alanine.pdb' > 'staging:///delete.pdb)
    Link('file://{}/alanine.pdb' > 'staging:///delete.pdb)


Local files
^^^^^^^^^^^

Let's mention these because they require special treatment. We cannot
(like RP can) copy files to the HPC, we need to store them in the DB
first.

.. code:: python

    new_pdb = File('file://../files/ntl9/ntl9.pdb').load()

Make sure you use ``file://`` to indicate that you are using a local
file. The above example uses a relative path which will be replaced by
an absolute one, otherwise we ran into trouble once we open the project
at a different directory.

.. code:: python

    print new_pdb.location


.. parsed-literal::

    file:///Users/jan-hendrikprinz/Studium/git/adaptivemd/examples/files/ntl9/ntl9.pdb


Note that now there are 3 ``/`` in the filename, two from the ``://``
and one from the root directory of your machine

The ``load()`` at the end really loads the file and when you save this
``File`` now it will contain the content of the file. You can access
this content as seen in the previous example.

.. code:: python

    print new_pdb.get_file()[:300]


.. parsed-literal::

    CRYST1   50.000   50.000   50.000  90.00  90.00  90.00 P 1
    ATOM      1  N   MET     1      33.720  28.790  34.120  0.00  0.00           N
    ATOM      2  H1  MET     1      33.620  29.790  33.900  0.00  0.00           H
    ATOM      3  H2  MET     1      33.770  28.750  35.120  0.00  0.00


For local files you normally use ``.transfer``, but ``copy``, ``move``
or ``link`` work as well. Still, there is no difference since the file
only exists in the DB now and copying from the DB to a place on the HPC
results in a simple file creation.

Now, we want to add a command to the staging and see what happens.

.. code:: python

    transaction = new_pdb.transfer()
    print transaction


.. parsed-literal::

    Transfer('file://{}/ntl9.pdb' > 'worker://ntl9.pdb)


.. code:: python

    task.append(transaction)

.. code:: python

    print task.description


.. parsed-literal::

    Task: TrajectoryGenerationTask(OpenMMEngine) [created]

    Sources
    - staging:///integrator.xml
    - staging:///alanine.pdb
    - staging:///openmmrun.py
    - file://{}/ntl9.pdb [exists]
    - staging:///system.xml
    Targets
    - sandbox:///{}/00000076/
    Modified

    <pretask>
    Link('staging:///alanine.pdb' > 'worker://initial.pdb)
    Link('staging:///system.xml' > 'worker://system.xml)
    Link('staging:///integrator.xml' > 'worker://integrator.xml)
    Link('staging:///openmmrun.py' > 'worker://openmmrun.py)
    Touch('worker://traj/')
    python openmmrun.py -r --report-interval 1 -p CPU --store-interval 1 -t worker://initial.pdb --length 100 worker://traj/
    Move('worker://traj/' > 'sandbox:///{}/00000076/)
    echo "This new line is pointless"
    Transfer('file://{}/ntl9.pdb' > 'worker://ntl9.pdb)
    <posttask>


We now have one more transfer command. But something else has changed.
There is one more files listed as required. So, the task can only run,
if that file exists, but since we loaded it into the DB, it exists (for
us). For example the newly created trajectory ``25.dcd`` does not exist
yet. Would that be a requirement the task would fail. But let's check
that it exists.

.. code:: python

    new_pdb.exists




.. parsed-literal::

    True



Okay, we have now the PDB file staged and so any real bash commands
could work with a file ``ntl9.pdb``. Alright, so let's output its stats.

.. code:: python

    task.append('stat ntl9.pdb')

Note that usually you place these stage commands at the top or your
script.

Now we could run this task, as before and see, if it works. (Make sure
you still have a worker running)

.. code:: python

    project.queue(task)

And check, that the task is running

.. code:: python

    task.state




.. parsed-literal::

    u'success'



If we did not screw up the task, it should have succeeded and we can
look at the STDOUT.

.. code:: python

    print task.stdout


.. parsed-literal::

    13:11:19 [worker:3] stdout from running task
    GO...
    Reading PDB
    Done
    Initialize Simulation
    Done.
    ('# platform used:', 'CPU')
    ('# temperature:', Quantity(value=300.0, unit=kelvin))
    START SIMULATION
    DONE
    Written to directory `traj/`
    This new line is pointless
    16777220 97338745 -rw-r--r-- 1 jan-hendrikprinz staff 0 1142279 "Mar 21 13:11:18 2017" "Mar 21 13:11:15 2017" "Mar 21 13:11:15 2017" "Mar 21 13:11:15 2017" 4096 2232 0 ntl9.pdb



Well, great, we have the pointless output and the stats of the newly
staged file ``ntl9.pdb``

How does a real script look like
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just for fun let's create the same scheduler that the
``adaptivemdworker`` uses, but from inside this notebook.

.. code:: python

    from adaptivemd import WorkerScheduler

.. code:: python

    sc = WorkerScheduler(project.resource)

If you really wanted to use the worker you need to initialize it and it
will create directories and stage files for the generators, etc. For
that you need to call ``sc.enter(project)``, but since we only want it
to parse our tasks, we only set the project without invoking
initialization. You should normally not do that.

.. code:: python

    sc.project = project

Now we can use a function ``.task_to_script`` that will parse a task
into a bash script. So this is really what would be run on your machine
now.

.. code:: python

    print '\n'.join(sc.task_to_script(task))


.. parsed-literal::

    set -e
    # This is part of the adaptivemd tutorial
    ln -s ../staging_area/alanine.pdb initial.pdb
    ln -s ../staging_area/system.xml system.xml
    ln -s ../staging_area/integrator.xml integrator.xml
    ln -s ../staging_area/openmmrun.py openmmrun.py
    mkdir -p traj/
    python openmmrun.py -r --report-interval 1 -p CPU --store-interval 1 -t initial.pdb --length 100 traj/
    mkdir -p ../../projects/tutorial/trajs/00000076/
    mv traj/* ../../projects/tutorial/trajs/00000076/
    rm -r traj/
    echo "This new line is pointless"
    # write file `ntl9.pdb` from DB
    stat ntl9.pdb


Now you see that all file paths have been properly interpreted to work.
See that there is a comment about a temporary file from the DB that is
then renamed. This is a little trick to be compatible with RPs way of
handling files. (TODO: We might change this to just write to the target
file. Need to check if that is still consistent)

A note on file locations
^^^^^^^^^^^^^^^^^^^^^^^^

One problem with bash scripts is that when you create the tasks you have
no concept on where the files actually are located. To get around this
the created bash script will be scanned for paths, that contain prefixed
like we are used to and are interpreted in the context of the worker /
scheduler. The worker is the only instance to know all that is necessary
so this is the place to fix that problem.

Let's see that in a little example, where we create an empty file in the
staging area.

.. code:: python

    task = Task()
    task.append('touch staging:///my_file.txt')

.. code:: python

    print '\n'.join(sc.task_to_script(task))


.. parsed-literal::

    set -e
    # This is part of the adaptivemd tutorial
    touch ../staging_area/my_file.txt


And voila, the path has changed to a relative path from the working
directory of the worker. Note that you see here the line we added in the
very beginning of example 1 to our resource!

A Task from scratch
~~~~~~~~~~~~~~~~~~~

If you want to start a new task you can begin with

.. code:: python

    task = Task()

as we did before.

Just start adding staging and bash commands and you are done. When you
create a task you can assign it a generator, then the system will assume
that this task was generated by that generator, so don't do it for you
custom tasks, unless you generated them in a generator. Setting this
allows you to tell a worker only to run tasks of certain types.

The Python RPC Task
-------------------

The tasks so far a very powerful, but they lack the possibility to call
a python function. Since we are using python here, it would be great to
really pretend to call a python function from here and not taking the
detour of writing a python bash executable with arguments, etc... An
example for this is the PyEmma generator which uses this capability.

Let's do an example of this as well. Assume we have a python function in
a file (you need to have your code in a file so far so that we can copy
the file to the HPC if necessary). Let's create the ``.py`` file now.

.. code:: python

    %%file my_rpc_function.py

    def my_func(f):
        import os
        print f
        return os.path.getsize(f)


.. parsed-literal::

    Overwriting my_rpc_function.py


Now create a PythonTask instead

.. code:: python

    task = PythonTask()

and the call function has changed. Note that also now you can still add
all the bash and stage commands as before. A PythonTask is also a
subclass of ``PrePostTask`` so we have a ``.pre`` and ``.post`` phase
available.

.. code:: python

    from my_rpc_function import my_func

We call the function ``my_func`` with one argument

.. code:: python

    task.call(my_func, f=project.trajectories.one)

.. code:: python

    print task.description


.. parsed-literal::

    Task: PythonTask(NoneType) [created]

    Sources
    - staging:///_run_.py
    - file://{}/_rpc_input_0x71bdd2d10e2f11e7a0f00000000002eaL.json
    - file://{}/my_rpc_function.py [exists]
    Targets
    - file://{}/_rpc_output_0x71bdd2d10e2f11e7a0f00000000002eaL.json
    Modified

    <pretask>
    Transfer('file://{}/_rpc_input_0x71bdd2d10e2f11e7a0f00000000002eaL.json' > 'worker://input.json)
    Link('staging:///_run_.py' > 'worker://_run_.py)
    Transfer('file://{}/my_rpc_function.py' > 'worker://my_rpc_function.py)
    python _run_.py
    Transfer('worker://output.json' > 'file://{}/_rpc_output_0x71bdd2d10e2f11e7a0f00000000002eaL.json)
    <posttask>


Well, interesting. What this actually does is to write the input
arguments to the function into a temporary ``.json`` file on the worker,
(in RP on the local machine and then transfers it to remote), rename it
to ``input.json`` and read it in the ``_run_.py``. This is still a
little clumsy, but needs to be this way to be RP compatible which only
works with files! Look at the actual script.

You see, that we really copy the ``.py`` file that contains the source
code to the worker directory. All that is done automatically. A little
caution on this. You can either write a function in a single file or use
any installed package, but in this case the same package needs to be
installed on the remote machine as well!

Let's run it and see what happens.

.. code:: python

    project.queue(task)

And wait until the task is done

.. code:: python

    project.wait_until(task.is_done)

The default settings will automatically save the content from the
resulting output.json in the DB an you can access the data that was
returned from the task at ``.output``. In our example the result was
just the size of a the file in bytes

.. code:: python

    task.output




.. parsed-literal::

    136



And you can use this information in an adaptive script to make
decisions.

success callback
^^^^^^^^^^^^^^^^

The last thing we did not talk about is the possibility to also call a
function with the returned data automatically on successful execution.
Since this function is executed on the worker we (so far) only support
function calls with the following restrictions.

1. you can call a function of the related generator class. for this you
   need to create the task using ``PythonTask(generator)``
2. the function name you want to call is stored in
   ``task.then_func_name``. So you can write a generator class with
   several possible outcomes and chose the function for each task.
3. The ``Generator`` needs to be part of ``adaptivemd``

So in the case of ``modeller.execute`` we create a ``PythonTask`` that
references the following functions

.. code:: python

    task = modeller.execute(project.trajectories)

.. code:: python

    task.then_func_name




.. parsed-literal::

    'then_func'



So we will call the default ``then_func`` of modeller or the class
modeller is of.

.. code:: python

    help(modeller.then_func)


.. parsed-literal::

    Help on function then_func in module adaptivemd.analysis.pyemma.emma:

    then_func(project, task, model, inputs)



These callbacks are called with the current project, the resulting data
(which is in the modeller case a ``Model`` object) and array of initial
inputs.

This is the actual code of the callback

.. code:: py

    @staticmethod
    def then_func(project, task, model, inputs):
        # add the input arguments for later reference
        model.data['input']['trajectories'] = inputs['kwargs']['files']
        model.data['input']['pdb'] = inputs['kwargs']['topfile']
        project.models.add(model)

All it does is to add some of the input parameters to the model for
later reference and then store the model in the project. You are free to
define all sorts of actions here, even queue new tasks.


.. autosummary::
    :toctree: api/generated/

    Task
    PythonTask
