.. _engine:

.. currentmodule:: adaptivemd

Engines
=======

The ``Trajectory`` object
~~~~~~~~~~~~~~~~~~~~~~~~~

Before we talk about adaptivity, let's have a look at possibilities to
generate trajectories.

We assume that you successfully ran a first trajectory using a worker.
Next, we talk about lot's of ways to generate new trajectories.

You will do this in the beginning. Remember we already have a PDB stored
from setting up the engine. if you want to start from this configuration
do as before

1. create the ``Trajectory`` object you want
2. make a task
3. submit the task to craft the object into existance on the HPC

A trajectory contains all necessary information to make itself. It has

1. a (hopefully unique) location: This will we the folder where all the
   files that belong to the trajectory go.
2. an initial frame: the initial configuration to be used to tell the MD
   simulation package where to start
3. a length in frames to run
4. the ``Engine``: the actual engine I want to use to create the
   trajectory.

Note, the ``Engine`` is technically not required unless you want to use
``.run()`` but it makes sense, because the engine contains information
about the topology and, more importantly information about which output
files are generated. This is the essential information you will need for
analysis, e.g. what is the filename of the trajectory file that contains
the protein structure and what is its stride?

Let's first build a ``Trajectory`` from scratch

.. code:: python

    file_name = next(project.traj_name)              # get a unique new filename

    trajectory = Trajectory(
        location=file_name,                          # this creates a new filename
        frame=pdb_file,                              # initial frame is the PDB
        length=100,                                  # length is 100 frames
        engine=engine                                # the engine to be used
    )

Since this is tedious to write there is a shortcut

.. code:: python

    trajectory = project.new_trajectory(
        frame=pdb_file,
        length=100,
        engine=engine,
        number=1          # if more then one you get a list of trajectories
    )

Like in the first example, now that we have the parameters of the
``Trajectory`` we can create the task to do that.

OpenMMEngine
------------

Let's do an example for an OpenMM engine. This is simply a small
python script that makes OpenMM look like a executable. It run a
simulation by providing an initial frame, OpenMM specific system.xml and
integrator.xml files and some additional parameters like the platform
name, how often to store simulation frames, etc.

.. code:: python

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://../files/alanine/system.xml').load(),
        integrator_file=File('file://../files/alanine/integrator.xml').load(),
        args='-r --report-interval 1 -p CPU'
    ).named('openmm')

We have now an OpenMMEngine which uses the previously made pdb ``File``
object and uses the location defined in there. The same for the OpenMM
XML files and some args to run using the ``CPU`` kernel, etc.

Last we name the engine ``openmm`` to find it later.

.. code:: python

    engine.name


Next, we need to set the output types we want the engine to generate. We
chose a stride of 10 for the ``master`` trajectory without selection and
a second trajectory with only protein atoms and native stride.

Note that the stride and all frame number ALWAYS refer to the native
steps used in the engine. In out example the engine uses ``2fs`` time
steps. So master stores every ``20fs`` and protein every ``2fs``

.. code:: python

    engine.add_output_type('master', 'master.dcd', stride=10)
    engine.add_output_type('protein', 'protein.dcd', stride=1, selection='protein')


Classes
-------

.. autosummary::
    :toctree: api/generated/

    Engine
    Trajectory
    OpenMMEngine
