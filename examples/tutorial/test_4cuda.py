#!/usr/bin/env python

import sys

# import adaptive components

from adaptivemd import Project
from adaptivemd import LocalCluster, AllegroCluster

from adaptivemd import OpenMMEngine4CUDA
from adaptivemd import PyEMMAAnalysis

from adaptivemd import File


if __name__ == '__main__':

    project = Project('testcase')

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    resource_id = 'fub.allegro'

    if len(sys.argv) > 2:
        exit()
    elif len(sys.argv) == 2:
        resource_id = sys.argv[1]

    if resource_id == 'local.jhp':
        project.initialize(LocalCluster())
    elif resource_id == 'local.sheep':
        project.initialize(LocalCluster())
    elif resource_id == 'fub.allegro':
        project.initialize(AllegroCluster())

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------
    pdb_file = File('file://../files/alanine/alanine.pdb').named('initial_pdb')

    engine = OpenMMEngine4CUDA(
        pdb_file=pdb_file,
        system_file=File('file://../files/alanine/system.xml'),
        integrator_file=File('file://../files/alanine/integrator.xml'),
        args='-r --report-interval 1 --store-interval 1'
    ).named('openmm')

    # --------------------------------------------------------------------------
    # CREATE AN ANALYZER
    #   the instance that knows how to compute a msm from the trajectories
    # --------------------------------------------------------------------------

    modeller = PyEMMAAnalysis(
        pdb_file=pdb_file
    ).named('pyemma')

    project.generators.add(engine)
    project.generators.add(modeller)

    # --------------------------------------------------------------------------
    # CREATE THE CLUSTER
    #   the instance that runs the simulations on the resource
    # --------------------------------------------------------------------------

    # print scheduler.rp_resource_name
    # print scheduler.resource.resource

    trajectories = project.new_trajectory(engine['pdb_file'], 100, 4)
    task = engine.task_run_trajectory(trajectories)

    project.tasks.add(task)

    project.wait_until(task.is_done)

    project.close()
