.. _generators:

.. currentmodule:: adaptivemd

Generators
==========

TaskGenerators are instances whose purpose is to create tasks to be
executed. This is similar to the way Kernels work. A TaskGenerator will
generate :class:`Task` objects for you which will be translated into a
:class:`radical.pilot.ComputeUnitDescription` and executed. In simple terms:

**The task generator creates the bash scripts for you that run a task.**

A task generator will be initialized with all parameters needed to make
it work and it will now what needs to be staged to be used.

Add generators to project
^^^^^^^^^^^^^^^^^^^^^^^^^

To add a generator to the project for later usage. You pick the
:meth:`Project.generators` store and just :meth:`Bundle.add` it.

Consider a store to work like a ``set()`` in python. It contains
objects only once and is not ordered.
Therefore we need a name to find the objects later. Of course you can
always iterate over all objects, but the order is not given.

To be precise there is an order in the time of creation of the object,
but it is only accurate to seconds and it really is the time it was
created and not stored.

.. code:: python

    project.generators.add(engine)
    project.generators.add(modeller)

Note, that you cannot add the same engine twice. But if you create a new
engine it will be considered different and hence you can store it again.


Classes
-------
.. autosummary::
    :toctree: api/generated/

    TaskGenerator
    Engine
    Analysis
