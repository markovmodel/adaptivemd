#!/usr/bin/env python

import sys, os

from adaptivemd import Project
from adaptivemd import LocalCluster

from adaptivemd import OpenMMEngine
from adaptivemd import PyEMMAAnalysis

from adaptivemd import File
from adaptivemd import WorkerScheduler

import mdtraj as md
import numpy as np


if __name__ == '__main__':

    Project.delete('example-simple-1')
    project = Project('example-simple-1')

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    project.initialize(LocalCluster())

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------

    pdb_file = File('file://../files/alanine/alanine.pdb').named('initial_pdb').load()

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://../files/alanine/system.xml').load(),
        integrator_file=File('file://../files/alanine/integrator.xml').load(),
        args='-r --report-interval 1 -p CPU --store-interval 1'
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

    trajectory = project.new_trajectory(engine['pdb_file'], 100, restart=True)
    task = engine.task_run_trajectory(trajectory)

    # project.queue(task)

    pdb = md.load('../files/alanine/alanine.pdb')
    cwd = os.getcwd()

    # this part fakes a running worker without starting the worker process
    worker = WorkerScheduler(project.resource)
    worker.enter(project)

    worker.submit(task)

    assert(len(project.trajectories) == 0)

    while not task.is_done():
        worker.advance()

    assert(len(project.trajectories) == 1)

    traj_path = os.path.join(
        worker.path,
        'workers',
        'worker.' + hex(task.__uuid__),
        worker.replace_prefix(project.trajectories.one.url)
    )

    assert(os.path.exists(traj_path))

    # go back to the place where we ran the test
    os.chdir(cwd)

    traj = md.load(traj_path, top=pdb)

    assert(len(traj) == 100)
    print traj[0].xyz
    print pdb[0].xyzk

    project.close()
