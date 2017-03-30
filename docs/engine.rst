.. _engine:

.. currentmodule:: adaptivemd

Engines
=======

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
    OpenMMEngine
