#!/usr/bin/env python

import os

from adaptivemd import Project
from adaptivemd import LocalResource

from adaptivemd import OpenMMEngine
from adaptivemd import PyEMMAAnalysis

from adaptivemd import File
from adaptivemd import WorkerScheduler

import mdtraj as md


if __name__ == '__main__':

    Project.delete('example-simple-1')
    project = Project('example-simple-1')

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    project.initialize(LocalResource())

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------

    pdb_file = File(
        'file://../../examples/files/alanine/alanine.pdb').named('initial_pdb').load()

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://../../examples/files/alanine/system.xml').load(),
        integrator_file=File('file://../../examples/files/alanine/integrator.xml').load(),
        args='-r --report-interval 1 -p CPU --store-interval 1'
    ).named('openmm')

    # --------------------------------------------------------------------------
    # CREATE AN ANALYZER
    #   the instance that knows how to compute a msm from the trajectories
    # --------------------------------------------------------------------------

    modeller = PyEMMAAnalysis(
        engine=engine
    ).named('pyemma')

    project.generators.add(engine)
    project.generators.add(modeller)

    # --------------------------------------------------------------------------
    # CREATE THE CLUSTER
    #   the instance that runs the simulations on the resource
    # --------------------------------------------------------------------------

    trajectory = project.new_trajectory(engine['pdb_file'], 100, engine)
    task = engine.run(trajectory)

    # project.queue(task)

    pdb = md.load('../../examples/files/alanine/alanine.pdb')
    cwd = os.getcwd()

    # we are using only the scheduling and excution logic, not a real
    # separate worker task
    scheduler = WorkerScheduler(project.resource)
    scheduler.enter(project)

    scheduler(task)

    assert(len(project.trajectories) == 0)

    while not task.is_done():
        scheduler.advance()

    assert(len(project.trajectories) == 1)

    traj_path = os.path.join(
        scheduler.path,
        'projects',
        'example-simple-1',
        'trajs',
        '00000000',
        'output.dcd'
    )

    assert(os.path.exists(traj_path))

    # go back to the place where we ran the test
    traj = md.load(traj_path, top=pdb)

    # 100 simulation steps + initial one should be 101 frames long
    assert(len(traj) == 101)

    # well, we have a 100 step trajectory which matches the size of the initial PDB
    # that is a good sign

    # extend the trajectory by 50
    task2 = task.extend(50)

    scheduler.submit(task2)

    while not task2.is_done():
        scheduler.advance()

    # should still be one, since we have the same trajectory
    assert(len(project.trajectories) == 1)

    traj = md.load(traj_path, top=pdb)

    assert (len(traj) == 151)

    # after extension it is 101 + 50 = 151 frames. Excellent

    project.close()
