.. _filestructure:

.. currentmodule:: adaptivemd

The folder structure
''''''''''''''''''''

For reference, this is the file structure of *adaptiveMD*.

::

    {shared_folder}/             # referenced by `shared://` and set in the `Resource`
      adaptivemd/                #                               set in the `Resource`
        projects/
          {project-name-1}/      # referenced by `project://`
            trajs/
              00000000/
              00000001/
              ...
            models/
        workers/                 # referenced by `sandbox://`
          staging_area/          # referenced by `staging://`
          worker.{task_UUID}/    # referenced by `worker://` (only the current one)
          ...

1. ``{shared_folder}``: is specific to your HPC or locally is usually
   chosen to be ``$HOME``. The 2. ``adaptivemd``: is the main folder
   where we will place all files. You can access the shared folder,
   there are no restrictions, but this should be restricted to loading
   input files like previous existing projects, etc. A stored files are
   place within this directory.
2. ``projects``: will contain a single folder per ``Project``, make sure
   that your project names are short but descriptive to later find
   files. All files you want to keep for later should be placed here.
3. ``workers``: this folder is specific to the worker scheduler (there
   is also the possibility to use *radical.pilot* which uses
   ``radical.pilot.sandbox``). It contains all temporary folders used by
   the workers to execute your tasks. Each task get a unique folder that
   also contains the UUID of the task to be handle. It is set up with
   all files and then in it your task is executed.
4. ``staging_area``: This is also a temporary folder that contains files
   that are used by the workers for multiple tasks. Normally a task
   generating factory knows which files it will need multiple times
5. ``trajs``: is a folder used by engines to place trajectories in.