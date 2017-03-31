#!/usr/bin/env python

import sys
import os

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
import time

from adaptivemd import Project, ExecutionPlan
from adaptivemd import AllegroCluster
from adaptivemd import ExecutionPlan

from adaptivemd import OpenMMEngine
from adaptivemd import PyEMMAAnalysis

from adaptivemd import File


if __name__ == '__main__':

    project = Project('testcase-4')

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    resource_id = 'fub.allegro'
    project.initialize(AllegroCluster())

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------
    pdb_file = File('file://../files/alanine/alanine.pdb').named('initial_pdb')

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://../files/alanine/system.xml'),
        integrator_file=File('file://../files/alanine/integrator.xml'),
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

    scheduler1 = project.get_scheduler('cpu', cores=4, runtime=4*24*60)
    scheduler2 = project.get_scheduler('cpu', cores=16, runtime=4*24*60)
    scheduler3 = project.get_scheduler('cpu', cores=1, runtime=4*24*60)

    # create 4 trajectories
    trajectories = project.new_trajectory(pdb_file, 100, 4)
    scheduler1(trajectories)
    scheduler1.wait()

    # now start adaptive loop
    def strategy_trajectory(scheduler, loops):
        for loop in range(loops):
            trajectories = project.new_ml_trajectory(length=20, number=4)
            tasks = scheduler(trajectories)
            yield tasks.is_done()

    ev1 = ExecutionPlan(strategy_trajectory(scheduler1, 100))
    project.add_event(ev1)

    ev2 = ExecutionPlan(strategy_trajectory(scheduler2, 25))
    project.add_event(ev2)

    def strategy_model(scheduler):
        while ev1 or ev2:
            num = len(project.trajectories)
            task = scheduler(modeller.execute(list(project.trajectories)))
            yield task.is_done
            cond = project.on_ntraj(num + 100)
            yield lambda: cond() or not ev1

    ev3 = ExecutionPlan(strategy_model(scheduler3))
    project.add_event(ev3)

    print

    CURSOR_UP_ONE = '\x1b[1A'
    ERASE_LINE = '\x1b[2K'

    # try:
    #     while project._events:
    #         sys.stdout.write('# of trajectories : %8d / # of models : %8d \n' % (
    #             len(project.trajectories),
    #             len(project.models)
    #         ))
    #         sys.stdout.flush()
    #         time.sleep(1.0)
    #         sys.stdout.write(CURSOR_UP_ONE + ERASE_LINE)
    # except KeyboardInterrupt:
    #     pass

    try:
        while project._events:
            time.sleep(2.0)
    except KeyboardInterrupt:
        pass

    scheduler1.exit()
    scheduler2.exit()
    scheduler3.exit()

    print 'DONE !!!'
    sys.stdout.write('# of trajectories : %8d / # of models : %8d \n' % (
        len(project.trajectories),
        len(project.models)
    ))

    project.close()
