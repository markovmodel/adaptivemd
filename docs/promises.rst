Why do we need a trajectory object?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You might wonder why a ``Trajectory`` object is necessary. You could
just build a function that will take these parameters and run a
simulation. At the end it will return the trajectory object. The same
object we created just now.

The main reason is to familiarize you with the general concept of
asyncronous execution and so-called *Promises*. The trajectory object we
built is similar to a *Promise* so what is that exactly?

A *Promise* is a value (or an object) that represents the result of a
function at some point in the future. In our case it represents a
trajectory at some point in the future. Normal promises have specific
functions do deal with the unknown result, for us this is a little
different but the general concept stands. We create an object that
represents the specifications of a ``Trajectory`` and so, regardless of
the existence, we can use the trajectory as if it would exists:

Get the length

.. code:: python

    print trajectory.length


.. parsed-literal::

    100


and since the length is fixed, we know how many frames there are and can
access them

.. code:: python

    print trajectory[20]


.. parsed-literal::

    Frame(sandbox:///{}/00000001/[20])


ask for a way to extend the trajectory

.. code:: python

    print trajectory.extend(100)


.. parsed-literal::

    <adaptivemd.engine.engine.TrajectoryExtensionTask object at 0x110e6e210>


ask for a way to run the trajectory

.. code:: python

    print trajectory.run()


.. parsed-literal::

    <adaptivemd.engine.engine.TrajectoryGenerationTask object at 0x110dd46d0>


We can ask to extend it, we can save it. We can reference specific
frames in it before running a simulation. You could even build a whole
set of related simulations this way without running a single frame. You
might understand that this is pretty powerful especially in the context
of running asynchronous simulations.

Last, we did not answer why we have two separate steps: Create the
trajectory first and then a task from it. The main reason is
educational: > **It needs to be clear that a ``Trajectory`` *can exist*
before running some engine or creating a task for it. The ``Trajectory``
*is not* a result of a simulation action.**