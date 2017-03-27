#!/usr/bin/env python

import sys

# import adaptive components

from adaptivemd import Project
from adaptivemd import AllegroCluster

from adaptivemd import OpenMMEngine

from adaptivemd import File


if __name__ == '__main__':

    project = Project('testcase')

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    resource = AllegroCluster()

    project.initialize(resource)

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------
    pdb_file = File('file://../files/alanine/alanine.pdb').named('initial_pdb')

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://../files/alanine/system.xml'),
        integrator_file=File('file://../files/alanine/integrator.xml'),
        args='-r --report-interval 1 --store-interval 1 -p CUDA'
    ).named('openmm')

    project.generators.add(engine)

    # --------------------------------------------------------------------------
    # CREATE THE CLUSTER
    #   the instance that runs the simulations on the resource
    # --------------------------------------------------------------------------

    # print scheduler.rp_resource_name
    # print scheduler.resource.resource

    trajectories = project.new_trajectory(engine['pdb_file'], 100, 4)
    tasks = map(engine.run, trajectories)

    project.queue(tasks)

    project.close()

    # FINALLY

    # use the slurm script that will start 4 workers using CUDA GPU and
    # sets the device number correctly
