#!/usr/bin/env python

import sys

# import adaptive components

from adaptivemd import (
    OpenMMEngine,
    AllegroCluster,
    Project,
    Brain,
    File,
    PyEMMAAnalysis,
    Event,
    LocalJHP, LocalSheep)


if __name__ == '__main__':

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    # use the resource specified as argument, fall back to localhost
    resource_id = 'local.jhp'

    if len(sys.argv) > 3:
        exit()

    project_id = sys.argv[1]
    project = Project(project_id)

    if len(sys.argv) == 3:
        resource_id = sys.argv[2]

        if resource_id == 'local.jhp':
            project.initialize(LocalJHP)
        elif resource_id == 'local.sheep':
            project.initialize(LocalSheep)
        elif resource_id == 'fub.allegro':
            project.initialize(AllegroCluster)

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------
    pdb_file = File('file://files/input.pdb')

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://files/system.xml'),
        integrator_file=File('file://files/integrator.xml'),
        args='-r --report-interval 1 -p CPU --store-interval 1')

    # --------------------------------------------------------------------------
    # CREATE THE MODELLER
    #   the instance to create msm models
    # --------------------------------------------------------------------------
    modeller = PyEMMAAnalysis(
        pdb_file=pdb_file,
        source_folder=File('../staging_area/ntl9/trajs'))

    # add the task generating capabilities
    project.register(engine)
    project.register(modeller)

    # todo: save the task_generators for later in the project

    with project:
        # lets get the default scheduler from the resource with all the
        scheduler = project.get_scheduler('gpu', cores=4)
        trajs = project.new_trajectory(pdb_file, 100, 4)

        # submit the trajectories
        scheduler.submit(trajs)

        def task_generator():
            return [
                engine.run(traj) for traj in
                scheduler.new_ml_trajectory(100, 2)]

        scheduler.add_event(
            Event()
            .on(scheduler.on_ntraj(range(10, 50, 10)))
            .do(task_generator))

        scheduler.add_event(
            Event()
            .on(scheduler.on_ntraj(10))
            .do(modeller.task_run_msm)
            .repeat().until(scheduler.on_ntraj(50)))

        # ----------------------------------------------------------------------
        # CREATE THE BRAIN
        #   the instance that knows what to do which the cluster
        # ----------------------------------------------------------------------

        # this will later replace setting up the events
        brain = Brain(scheduler)  # this needs to be smarter

        scheduler.trigger()
        scheduler.wait()

# ------------------------------------------------------------------------------
