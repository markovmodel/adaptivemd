#!/usr/bin/env python

import sys

# WE RELY ON THESE BEING SET !!!

# set default verbose level
# verbose = os.environ.get('RADICAL_PILOT_VERBOSE', 'REPORT')
# os.environ['RADICAL_PILOT_VERBOSE'] = verbose

# set default URL to IMP Mongo DB
# path_to_db = os.environ.get(
#     'RADICAL_PILOT_DBURL', "mongodb://ensembletk.imp.fu-berlin.de:27017/rp")

# assume we run a local
# path_to_db = os.environ.get(
#     'RADICAL_PILOT_DBURL', "mongodb://localhost:27017/rp")
#
# os.environ['RADICAL_PILOT_DBURL'] = path_to_db

# import adaptive components

from adaptivemd import Project
from adaptivemd import AllegroCluster

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
        args='-r --report-interval 10 --store-interval 10'
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

    scheduler = project.get_scheduler('gpu', cores=1, runtime=4*24*60)

    # create 4 blocks a 4 trajectories
    trajectories = [project.new_trajectory(engine['pdb_file'], 100, 4) for _ in range(4)]
    tasks = map(engine.run, trajectories)

    print trajectories

    # submit
    scheduler(tasks)

    scheduler.wait()

    # now start adaptive loop

    for f in project.trajectories:
        print f.url

    for loop in range(2):
        trajectories = [project.new_ml_trajectory(length=100, number=4) for _ in range(4)]
        print trajectories
        tasks = map(engine.run, trajectories)

        finals = scheduler(tasks)
        scheduler.wait()

        for f in project.trajectories:
            print f.url

        task = scheduler(modeller.execute(list(project.trajectories)))
        scheduler.wait()

    # print
    #
    # CURSOR_UP_ONE = '\x1b[1A'
    # ERASE_LINE = '\x1b[2K'
    #
    # while ev:
    #     sys.stdout.write(CURSOR_UP_ONE + ERASE_LINE)
    #     sys.stdout.write('# of trajectories : %8d / # of models : %8d \n' % (
    #         len(project.trajectories),
    #         len(project.models)
    #     ))
    #     sys.stdout.flush()
    #     time.sleep(5.0)

    scheduler.exit()

    project.close()
