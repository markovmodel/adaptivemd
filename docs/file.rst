.. _file:

.. currentmodule:: adaptivemd

Files
=====

The :class:`File` object. Instead of just a string, these are
used to represent files anywhere, on the cluster or your local
application. There are some subclasses or *extensions* of :class:`File` that
have additional meta information like :class:`Trajectory` or :class:`Frame`. The
underlying base object of a :class:`File` is called a :class:`Location`.

All of these objects share the :py:attr:`.~Location.location` property. A string that
represents a location for a file in general.

.. code:: python

    f = File('system.pdb')

This representation is so far useless unless we specify where this file
is located. It could be on the HPC somewhere or on the local computer.
To do that we use prefixes

1. ``{drive}://{relative_path}`` or
2. ``{drive}:///{absolute_path}`` (for local files)

You can use the following prefixes

-  ``file://`` points to files on your local machine.
-  ``worker://`` specifies files on the current working directory of the
   executing node. Usually these are temprary files for a single
   execution.
-  ``shared://`` specifies the root shared FS directory (e.g.
   ``NO_BACKUP/`` on Allegro) Use this to import and export files that
   are already on the cluster.
-  ``staging://`` a special scheduler-specific *caching* directory. Use
   this to relate to files that should be reused, but not stored
   long-time. A typical example is a PDB file. This is required by every
   simulation but an input file. You want to copy it once to the cluster
   and use it over and over.
-  ``sandbox://`` this is a specia folder where all temporary worker
   directories are located. It also contains the session folders for RP.
-  ``project://`` this folder contains all the project data for your
   current project and is the place where all the data should be stored
   for long-time storage

Later you might want to transfer a file from a project folder to the
current working directory (whereever this will be) and you would specify
locations in this way

::

    project://models/my_model.json >> worker://input_model.json

We start with a first PDB file that is located on this machine at a
relative path

.. code:: python

    pdb_file = File('file://../files/alanine/alanine.pdb')

``File`` like any complex object in adaptivemd can have a ``.name``
attribute that makes them easier to find later. You can either set the
``.name`` property after creation, or use a little helper method
``.named()`` to get a one-liner. This function will set ``.name`` and
return itself.

.. code:: python

    pdb_file.name = 'initial_pdb'

The ``.load()`` at the end is important. It causes the ``File`` object
to load the content of the file and if you save the ``File`` object, the
actual file is stored with it. This way it can simply be rewritten on
the cluster or anywhere else.

.. code:: python

    pdb_file.load()




.. parsed-literal::

    'alanine.pdb'



Now you can access the content

.. code:: python

    print pdb_file.get_file()[:500]


.. parsed-literal::

    REMARK   1 CREATED WITH MDTraj 1.8.0, 2016-12-22
    CRYST1   26.063   26.063   26.063  90.00  90.00  90.00 P 1           1
    MODEL        0
    ATOM      1  H1  ACE A   1      -1.900   1.555  26.235  1.00  0.00          H
    ATOM      2  CH3 ACE A   1      -1.101   2.011  25.651  1.00  0.00          C
    ATOM      3  H2  ACE A   1      -0.850   2.954  26.137  1.00  0.00          H
    ATOM      4  H3  ACE A   1      -1.365   2.132  24.600  1.00  0.00          H
    ATOM      5  C   ACE A   1       0.182


There are a few other things that you can access from a file. There is a
time when it was initiated (like any storable object).

.. code:: python

    print 'timestamp', pdb_file.__time__
    print 'uuid', hex(pdb_file.__uuid__)


.. parsed-literal::

    timestamp 1490777436
    uuid 0x5eadd73145711e7a9d3000000000042L


Access the drive (prefix)

.. code:: python

    print pdb_file.drive


.. parsed-literal::

    file


Get the path on the drive (see we have converted the relative path to an
absolute)

.. code:: python

    print '...' + pdb_file.dirname[35:]


.. parsed-literal::

    .../adaptivemd/examples/files/alanine


or the basename

.. code:: python

    print pdb_file.basename


.. parsed-literal::

    alanine.pdb


Classes
-------

.. autosummary::
    :toctree: api/generated/

    Location
    File
    Trajectory
    Frame
    JSONFile
    ~mongodb.DataDict