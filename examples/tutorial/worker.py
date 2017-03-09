#!/usr/bin/env python

import os

path_to_db = os.environ.get(
    'RADICAL_PILOT_DBURL', "mongodb://localhost:27017/rp")

os.environ['RADICAL_PILOT_DBURL'] = path_to_db

# import adaptive components
import argparse

from adaptivemd import Project, Worker
from adaptivemd.mongodb import MongoDBStorage

# leave this in here to be able to load these objects


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run an AdaptiveMD worker')

    parser.add_argument(
        'project',
        metavar='project_name',
        help='project name the worker should attach to',
        type=str)

    parser.add_argument(
        '-t', '--walltime', dest='walltime',
        type=int, default=0, nargs='?',
        help='minutes until the worker shuts down. If 0 (default) it will run indefinitely')

    parser.add_argument(
        '-d', '--mongodb', dest='mongo_db_path',
        type=str, default='mongodb://ensembletk.imp.fu-berlin.de:27017/adaptivemd', nargs='?',
        help='the mongodb url to the db server')

    parser.add_argument(
        '-g', '--generators', dest='generators',
        type=str, default='', nargs='?',
        help='a comma separated list of generator names used to dispatch the tasks. '
             'the worker will only respond to tasks from generators whose names match '
             'one of the names in the given list. Example: --generators=openmm will only '
             'run scripts from generators named `openmm`')

    parser.add_argument(
        '-l', '--local',
        dest='local', action='store_true',
        default=False,
        help='if true then the DB is set to the default local port')

    parser.add_argument(
        '-a', '--allegro',
        dest='allegro', action='store_true',
        default=False,
        help='if true then the DB is set to the default allegro setting')

    parser.add_argument(
        '--sheep',
        dest='sheep', action='store_true',
        default=False,
        help='if true then the DB is set to the default sheep setting')

    parser.add_argument(
        '-s', '--sleep', dest='sleep',
        type=int, default=2, nargs='?',
        help='polling interval for new jobs in seconds. Default is 2 seconds. Increase '
             'to get less traffic on the DB')

    args = parser.parse_args()

    if args.allegro:
        db_path = "mongodb://ensembletk.imp.fu-berlin.de:27017/"
    elif args.sheep:
        db_path = "mongodb://sheep:27017/"
    elif args.local:
        db_path = "mongodb://localhost:27017/"
    else:
        db_path = args.mongo_db_path

    MongoDBStorage._db_url = db_path

    project = Project(args.project)

    print project.resource

    print project.trajectories

    # --------------------------------------------------------------------------
    # CREATE THE WORKER
    #   the instance that knows about the current state
    # --------------------------------------------------------------------------

    worker = Worker(
        walltime=args.walltime,
        generators=args.generators,
        sleep=args.sleep,
        heartbeat=10.0

    )
    project.workers.add(worker)
    worker.create(project)

    print 'Worker running @ %s' % db_path,

    if args.generators:
        print '[limited to generators `%s`]' % ', '.join(worker.generators),

    print

    worker.run()

    exit()
