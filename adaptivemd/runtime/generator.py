
import os
import sys
import yaml
#from pprint import pformat
#import uuid
#import time
from pprint import pformat

from .control import queue_tasks, check_trajectory_minlength
from .util import counter

from ..sampling import get_sampling_function
from ..util import get_logger
logger = get_logger(__name__)


__all__ = ["workflow_generator_simple"]


def workflow_generator_simple(
    project, engine, n_traj, n_steps, round_n,
    longest = 5000,
    n_rounds = 1,
    modeller = None,
    sfkwargs = dict(),
    minlength = None,
    batchsize = 999999,
    batchwait = False,
    batchsleep = 5,
    progression = 'any',
    cpu_threads = 8,
    fixedlength = True,
    startontraj = 0, # TODO None and extra condition if set
    admd_profile = None,
    analysis_cfg = None,
    min_model_trajlength = 0, # TODO None and extra condition if set
    sampling_function_name = 'explore_macrostates',

    # these arent currently utilized
    randomly = False,
    mpi_ranks = 0,
    continuing = True,
    **kwargs,):

    logger.info("Starting workflow_generator_simple function")
    sampling_function = get_sampling_function(
        sampling_function_name, **sfkwargs,
    )

    resource_requirements = dict() # TODO calculate request
    qkwargs = dict(sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

    if progression == 'all':
        progress = lambda tasks: all([ta.is_done() for ta in tasks])

    else:
        progress = lambda tasks: any([ta.is_done() for ta in tasks])

    if n_rounds:

        assert isinstance(n_rounds, int)
        assert n_rounds > 0

        logger.info("Going to do n_rounds:  {}".format(n_rounds))

    c = counter(n_rounds)
    tasks = list()

    # PREPARATION - Preprocess task setups
    logger.info("Using MD Engine: {0} {1}".format(engine, engine.name))#, project.generators[engine.name].__dict__)
    logger.info("Using fixed length? {}".format(fixedlength))

    if minlength is None:
        minlength = n_steps

    logger.info("\nProject models\n - Number: {n_model}"
          .format(n_model=len(project.models)))

    logger.info("\nProject trajectories\n - Number: {n_traj}"
          .format(n_traj=len(project.trajectories)))

    logger.debug("\nProject trajectories\n - Lengths:\n{lengths}"
          .format(lengths=[t.length for t in project.trajectories]))

    # ROUND 1 - No pre-existing data
    if len(project.trajectories) == 0:
        notfirsttime = False

        logger.info("Defining first simulation tasks for new project")

        for traj in project.new_trajectory(engine['pdb_file'], n_steps, engine, n_traj):
            tasks.append(traj.run(**resource_requirements))
            if admd_profile: # This should be path to an RC file
                tasks[-1].pre.insert(0, "source %s" % admd_profile)

        if not c.done:
            logger.info("Project first tasks queue")
            queue_tasks(project, tasks, **qkwargs)
            c.increment()

        logger.info("Project first tasks queued")
        logger.info("Queued First Tasks in new project")

        yield lambda: progress(tasks)

        logger.info("First Tasks are done")
        logger.info("Project first tasks done")

    else:

        notfirsttime = True

    mtask = None

    if modeller:
        if analysis_cfg:
            with open(analysis_cfg, 'r') as f:
                _margs = yaml.safe_load(f)

            update_margs = lambda rn: _margs[
                max(list(filter(
                lambda mi: mi <= rn, _margs)))
            ]

        else:
            raise RuntimeError("Must specify an analysis cfg file to use modeller")

    # Start of CONTROL LOOP
    while not c.done:

        logger.info("Checking Extension Lengths")

        # TODO fix, this isn't a consistent name "trajectories"
        trajectories = set()
        # This loop will escape if all the trajectories
        # are / become full length
        priorext = -1
        while priorext and not c.done:

            xtasks = list()

            #active_trajs =  ~~~  after_n_trajs_trajs
            after_n_trajs_trajs = list(project.trajectories.sorted(
                lambda tj: tj.__time__))[startontraj:]

            logger.info(
                "Checking last {} trajectories for proper length".format(
                len(after_n_trajs_trajs))
            )

            xtasks = check_trajectory_minlength(
                project, minlength, after_n_trajs_trajs, n_steps, n_traj,
                resource_requirements=resource_requirements
            )

            # NOTE we are tracking pre-existing extension tasks
            tnames = set()
            if len(trajectories) > 0:
                [tnames.add(_) for _ in set(zip(*trajectories)[0])]

            # NOTE so we only extend those who aren't already running
            queuethese = list()
            for xta in xtasks:
                tname = xta.trajectory.basename

                if tname not in tnames:
                    tnames.add(tname)
                    trajectories.add( (tname, xta) )
                    queuethese.append(xta)

            if queuethese:

                queue_tasks(project, queuethese, **qkwargs)
                yield lambda: progress(queuethese)

            # NOTE and remove any that have already completed
            removals = list()
            for tname, xta in trajectories:
                if xta.state in {"fail","halted","success","cancelled"}:
                    removals.append( (tname, xta) )

            for removal in removals:
                trajectories.remove(removal)

            if len(trajectories) == n_traj and priorext < n_traj:
                logger.info("Have full width of extensions")
                c.increment()

            # setting this to look at next round
            priorext = len(trajectories)

        logger.info("----------- On workload #{0}".format(c.n))
        logger.info("Runtime main loop enter")
        tasks = list()

        if not modeller:
            logger.info("Extending project without modeller")

            trajectories = sampling_function(project, engine, n_steps, n_traj)
            logger.info("Runtime new trajectories defined")

            logger.info("Converting trajectories to tasks")
            [tasks.append(t.run(**resource_requirements)) for t in trajectories]

            logger.info("Runtime new tasks queueing")
            if tasks:
                queue_tasks(project, tasks, **qkwargs)
                logger.info("Runtime new tasks queued")

            c.increment()

            yield lambda: progress(tasks)

            logger.info("Runtime main no modeller done")

        else:

            if mtask is None:

                margs = update_margs(round_n)
                margs.update(resource_requirements)

                logger.info("Extending project with modeller")
                logger.info("Analysis args for this round will be: {}".format(pformat(margs)))

                trajectories = list(filter(lambda tj: tj.length >= min_model_trajlength, project.trajectories))
                mtask = modeller.execute(trajectories, **margs)
                project.queue(mtask)

                yield lambda: progress(tasks)

            elif mtask.is_done():
                # In current 1-workload per runtime model, shouldn't ever see this condition

                logger.info("Current modelling task is done")
                mtask = None

            else:
                # In current 1-workload per runtime model, shouldn't ever see this condition

                logger.info("Waiting on modelling task")
                yield lambda: progress(tasks)


