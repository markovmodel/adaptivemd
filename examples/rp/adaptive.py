#!/usr/bin/env python

import os
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

import radical.pilot as rp
import radical.utils as ru

# import adaptive components

from adaptivemd import OpenMMEngine, AllegroCluster, Brain, MDCluster, \
    LocalResource, File, PyEMMAAnalysis
import adaptivemd.misc as amp


if __name__ == '__main__':

    verbose = os.environ.get('RADICAL_PILOT_VERBOSE', 'REPORT')

    # we use a reporter class for nicer output
    report = ru.LogReporter(name='radical.pilot', level=verbose)
    report.title('Getting Started (RP version %s)' % rp.version)

    # use the resource specified as argument, fall back to localhost
    resource_id = 'local.jhp'

    if len(sys.argv) > 2:
        report.exit('Usage:\t%s [resource]\n\n' % sys.argv[0])
        exit()
    elif len(sys.argv) == 2:
        resource_id = sys.argv[1]

    # --------------------------------------------------------------------------
    # CREATE THE RESOURCE
    #   the instance to know about the place where we run simulations
    # --------------------------------------------------------------------------

    if resource_id == 'local.jhp':
        resource = LocalResource(15, 2)
        resource.add_path(amp.path_conda_local_jhp)
    elif resource_id == 'local.sheep':
        resource = LocalResource(15, 2)
        resource.add_path(amp.path_conda_local_sheep)
    elif resource_id == 'fub.allegro':
        resource = AllegroCluster(15, 4, 'big')
        resource.add_path(amp.path_conda_allegro_jhp)
    else:
        resource = LocalResource(1, 2)

    # --------------------------------------------------------------------------
    # CREATE THE ENGINE
    #   the instance to create trajectories
    # --------------------------------------------------------------------------
    pdb_file = File('file://input.pdb')

    engine = OpenMMEngine(
        pdb_file=pdb_file,
        system_file=File('file://system.xml'),
        integrator_file=File('file://integrator.xml')
    )

    engine.args = '-r --report-interval 1 -p fastest --store-interval 1'

    # --------------------------------------------------------------------------
    # CREATE THE CLUSTER
    #   the instance that runs the simulations on the resource
    # --------------------------------------------------------------------------

    cluster = MDCluster(
        system='alanine',
        resource=resource,
        report=report)

    # add the path to CONDA if now already in the default
    cluster.add_path(os.environ.get('CONDA_BIN'))

    # --------------------------------------------------------------------------
    # CREATE AN ANALYZER
    #   the instance that knows how to compute a msm from the trajectories
    # --------------------------------------------------------------------------

    msmb = PyEMMAAnalysis(pdb_file, File('../staging_area/ntl9/trajs'))
    msmb.args = '-k 2 -l 1 -c 2'

    # --------------------------------------------------------------------------
    # CREATE THE BRAIN
    #   the instance that knows what to do which the cluster
    # --------------------------------------------------------------------------
    brain = Brain(msmb)

    with cluster:
        resource.add_shared(cluster)

        report.info('stage shared data from generators')
        cluster.stage_in(engine.stage_in)
        cluster.stage_in(msmb.stage_in)

        report.ok('>>ok\n')

        brain.execute(cluster)

        # wait until no more units are running and hence all results are finite
        cluster.wait()

    report.header('generated new trajectories')

    for n, f in enumerate(cluster.trajectories.sorted(lambda x: x.created)):
        print(repr(f))

    report.header('generated new models')

    for n, f in enumerate(
            cluster
            .files
            .v(lambda x: x.basename.endswith('.msm'))
            .sorted(lambda x: x.created)
    ):
        print(repr(f))

    for n, m in enumerate(cluster.models):
        print m

    report.header()

# -------------------------------------------------------------------------------
