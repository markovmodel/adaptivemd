#!/usr/bin/env python

import sys

# import adaptive components

from adaptivemd import (
    OpenMMEngine,
    AllegroCluster,
    Project,
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

    if len(sys.argv) > 3 or len(sys.argv) < 2:
        exit()

    project_name = sys.argv[1]

    project = Project(project_name)

    if len(sys.argv) == 3:

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

    # --------------------------------------------------------------------------
    # CREATE THE SESSION
    #   the instance that runs the simulations on the resource
    # --------------------------------------------------------------------------

    # add the task generating capabilities
    project.register(engine)
    project.register(modeller)

    project.open()

    scheduler = project.get_scheduler(cores=2)
    trajs = project.new_trajectory(pdb_file, 100, 4)

    # submit the trajectories
    scheduler.submit(trajs)

    def task_generator():
        return [
            engine.run(traj) for traj in
            project.new_ml_trajectory(100, 2)]


    scheduler.add_event(
        Event().on(project.on_ntraj(range(4, 50, 2))).do(task_generator)
    )

    # todo: change that this will stop when the first event is done
    scheduler.add_event(
        Event()
            .on(project.on_ntraj(10))
            .do(modeller.task_run_msm)
            .repeat().until(project.on_ntraj(
            20)))

    # ----------------------------------------------------------------------
    # CREATE THE BRAIN
    #   the instance that knows what to do which the cluster
    # ----------------------------------------------------------------------

    # this will later replace setting up the events
    # brain = Brain(cluster)  # this needs to be smarter

    scheduler.wait()

    project.close()

# ------------------------------------------------------------------------------
