#!/usr/bin/env python

import sys
import os
import time

# WE RELY ON THESE BEING SET !!!

# set default verbose level
# verbose = os.environ.get('RADICAL_PILOT_VERBOSE', 'REPORT')
# os.environ['RADICAL_PILOT_VERBOSE'] = verbose

# set default URL to IMP Mongo DB
# path_to_db = os.environ.get(
#     'RADICAL_PILOT_DBURL', "mongodb://ensembletk.imp.fu-berlin.de:27017/rp")

# assume we run a local
path_to_db = os.environ.get(
    'RADICAL_PILOT_DBURL', "mongodb://localhost:27017/rp")

os.environ['RADICAL_PILOT_DBURL'] = path_to_db

# import adaptive components

from adaptivemd import Project, ExecutionPlan
from adaptivemd import LocalJHP
from adaptivemd import ExecutionPlan

from adaptivemd import OpenMMEngine
from adaptivemd import PyEMMAAnalysis

from adaptivemd import File


if __name__ == '__main__':

    project = Project('testcase-worker')

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    # resource_id = 'fub.allegro'
    project.initialize(LocalJHP())

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------
    pdb_file = File('file://../files/alanine/alanine.pdb').named('initial_pdb').load()

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://../files/alanine/system.xml').load(),
        integrator_file=File('file://../files/alanine/integrator.xml').load(),
        args='-r --report-interval 10 --store-interval 1 -p CPU'
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

    # create 4 trajectories
    trajectories = project.new_trajectory(pdb_file, 100, 4)
    tasks = map(engine.run, trajectories)
    map(project.tasks.add, tasks)

    # now start adaptive loop
    def strategy_trajectory(loops, num):
        for loop in range(loops):
            trajectories = project.new_ml_trajectory(20, number=num)
            tasks = map(engine.run, trajectories)
            map(project.tasks.add, tasks)
            yield [t.is_done for t in tasks]

    ev1 = ExecutionPlan(strategy_trajectory(100, 10))

    project.add_event(ev1)

    def strategy_model(steps):
        while ev1:
            num = len(project.trajectories)
            task = modeller.execute(list(project.trajectories))
            project.tasks.add(task)
            yield task.is_done
            cond = project.on_ntraj(num + steps)
            yield lambda: cond() or not ev1

    ev2 = ExecutionPlan(strategy_model(100))
    project.add_event(ev2)

    try:
        while project._events:
            print len(project.tasks)
            time.sleep(5.0)
            project.trigger()

    except KeyboardInterrupt:
        pass

    print 'Shutting down workers!'

    for w in project.workers:
        w.command('shutdown')

    print 'DONE !!!'
    sys.stdout.write('# of trajectories : %8d / # of models : %8d \n' % (
        len(project.trajectories),
        len(project.models)
    ))

    project.close()
