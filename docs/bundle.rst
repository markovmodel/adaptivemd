.. _bundle:

.. currentmodule:: adaptivemd

Bundles
=======

A :class:`Bundle` - A set-enhancement to add filtering and store handling capabilities

Bundles can be accessed like a normal set using iteration. You can add objects
using ``.add(item)`` if the bundle is not a view

Examples
--------

Some basic functions

.. code-block:: python

    bundle = Bundle(['10', '20', 1, 2, 3])
    str_view = bundle.c(basestring)  # only how strings
    print list(str_view)  # ['10', '20']
    fnc_view = bundle.v(lambda x: int(x) < 3)
    print list(fnc_view) # [1, 2]

Some :class:`File` specific functions

.. code-block:: python

    import adaptivemd as amd
    bundle = Bundle([amd.File('0.dcd'), amd.File('a.pdb')])
    file_view = bundle.f('*.dcd')
    print list(file_view)  # [File('0.dcd')]

Logic operations produce view on the resulting bundle

.. code-block:: python

    and_bundle = str_view & fnc_view
    print list(and_bundle)  # []
    and_bundle = str_view | fnc_view
    print list(and_bundle)  # [1, 2, '10', '20']

A :class:`StoredBundle` is attached to a mongodb store (a stored object list).
Adding will append the object to the store if not stored yet. All iteration
and views will always be kept synced with the DB store content.

.. code-block:: python

    p = amd.Project('test-project')
    store = StoredBundle()  # new bundle
    store.set_store(p.storage.trajectories)  # attach to DB
    print list(store)  # show all trajectories
    len_store = store.v(lambda x: len(x) > 10)  # all trajs with len > 10
    print list(len_store)

Set do not have ordering so some functions do not make sense. As long as
you are working with storable objects (subclassed from :class:`adaptivemd.mongodb.StorableMixin`)
you have some time-ordering (accurate to seconds)

.. code-block:: python

    print store.first  # get the earlist created object
    print store.one    # get one (any) single object
    print store.last   # get the last created object

A bundle is mostly meant to work with storable objects (but does not have to)
To simplify access to certain attributes or apply function to all members you
can use the :meth:`BaseBundle.all` attribute and get a *delegator* that will
apply an attribute or method to all objects

.. code-block:: python

    print len_store.all.length  # print all lengths of all objects in len_store
    print store.all.path  # print all path of all trajectories
    # call `.execute('shutdown') on all workers in the `.workers` bundle
    print p.workers.all.execute('shutdown')

Classes
-------

.. autosummary::
    :toctree: api/generated/

    Bundle
    StoredBundle
    SortedBundle
    ViewBundle
    BaseBundle
    LogicBundle
    AndBundle
    OrBundle
    BundleDelegator
    FunctionDelegator
