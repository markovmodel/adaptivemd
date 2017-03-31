.. _resource:

.. currentmodule:: adaptivemd

Resources
=========

A :class:`Resource` specifies a shared filesystem with one or more clusteres
attached to it. This can be your local machine or just a regular cluster
or even a group of cluster that can access the same FS (like Titan, Eos
and Rhea do).

Once you have chosen your place to store your results t is set
for the project and can (at least should) not be altered since all file
references are made to match this resource.

Let us pick a local resource on your laptop or desktop machine; no
cluster / HPC involved for now.

.. code:: python

    from adaptivemd import LocalResource

We now create the Resource object

.. code:: python

    resource = LocalResource()

Since this object defines the path where all files will be placed, let's
get the path to the shared folder. The one that can be accessed from all
workers. On your local machine this is trivially the case.

.. code:: python

    resource.shared_path




.. parsed-literal::

    '$HOME/adaptivemd/'



Okay, files will be placed in ``$HOME/adaptivemd/``. You can change this
using an option when creating the ``Resource``

.. code:: python

    LocalCluster(shared_path='$HOME/my/adaptive/folder/')

Configuring your resource
'''''''''''''''''''''''''

Now you can add some additional paths, conda environment, etc, before we
setup the project. This works by setting a special task ``.wrapper``
(see notebook 4 for more things you can do with ``Task`` objects.)

.. code:: python

    resource.wrapper




.. parsed-literal::

    <adaptivemd.task.DummyTask at 0x110d93d50>



In a nutshell, this dummy task has a ``.pre`` and ``.post`` list of
commands you can add any command you want to be executed before every
task you run.

.. code:: python

    resource.wrapper.pre.append('echo "Hello World"')

A task can also automatically add to the ``PATH`` variable, set
environment variables and you can add conda environments

.. code:: python

    resource.wrapper.add_conda_env('my_env_python_27')

.. code:: python

    resource.wrapper.add_path('/x/y/z')

.. code:: python

    resource.wrapper.environment['CONDA'] = 'True'

.. code:: python

    print resource.wrapper.description


.. parsed-literal::

    Task: DummyTask
    <pre>
    export PATH=/x/y/z:$PATH
    export CONDA=True
    echo "Hello World"
    </pre>
    <main />
    <post>
    </post>


Let's reset that now and just add a little comment

.. code:: python

    resource = LocalResource()
    resource.wrapper.pre.append('# This is part of the adaptivemd tutorial')

Finalize the ``Resource``
'''''''''''''''''''''''''

Last, we save our configured :class:`Resource` and initialize our empty
prohect with it. This is done once for a project and should not be
altered.

.. code:: python

    project.initialize(resource)


Classes
-------

.. autosummary::
    :toctree: api/generated/

    LocalResource