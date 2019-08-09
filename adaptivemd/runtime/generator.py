
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


__all__ = ["workflow_generator_simple", "model_extend_simple"]


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
    startontraj = 0,
    admd_profile = None,
    analysis_cfg = None,
    min_model_trajlength = 0,
    sampling_function_name = 'explore_macrostates',

    # these arent currently utilized
    randomly = False,
    mpi_ranks = 0,
    continuing = True,
    **kwargs,):

    logger.info("Starting workflow_generator_simple function")
    sampling_function = get_sampling_function(
        sampling_function_name, **sfkwargs
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

    if analysis_cfg:
        with open(analysis_cfg, 'r') as f:
            _margs = yaml.safe_load(f)

        update_margs = lambda rn: _margs[
            max(list(filter(
            lambda mi: mi <= rn, _margs)))
        ]

    # Start of CONTROL LOOP
    while not c.done:

        logger.info("Checking Extension Lengths")

        priorext = -1
        # TODO fix, this isn't a consistent name "trajectories"
        trajectories = set()
        # This loop will escape if all the trajectories
        # are / become full length
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

            yield lambda: model_extend_simple(project, engine, modeller, n_traj, tasks, n_steps, sampling_function, mtask=mtask, c=c)

            logger.info("Runtime main no modeller done")

        else:
            margs = update_margs(round_n)

            logger.info("Extending project with modeller")
            logger.info("Analysis args for this round will be: {}".format(pformat(margs)))

            if mtask is None:

                yield lambda: model_extend_simple(project, engine, modeller, n_traj, tasks, n_steps, sampling_function, mtask=mtask, c=c)

                logger.info("Runtime main loop1 done")
                mtask = tasks[-1]
                logger.info("Set a current modelling task: {}".format(mtask))

            # TODO don't assume mtask not None means it
            #      has is_done method. outer loop needs
            #      upgrade
            elif mtask.is_done():

                logger.info("Current modelling task is done")

                yield lambda: model_extend_simple(project, engine, modeller, n_traj, tasks, n_steps, sampling_function, mtask=mtask, c=c)

                logger.info("Runtime main loop2 done")
                logger.info("Added another model to project, now have: {}".format(len(project.models)))
                mtask = tasks[-1]
                logger.info("Set a new current modelling task")

            elif not mtask.is_done():
                logger.info("Continuing trajectory tasks, waiting on model")
                yield lambda: model_extend_simple(project, engine, modeller, n_traj, tasks, n_steps, sampling_function, mtask=mtask, c=c)
                logger.info("Runtime main loop3 done")

            else:
                logger.info("Not sure how we got here")
                pass


def model_extend_simple(project, engine, modeller, n_traj,
     tasks, n_steps, sampling_function, mtask, c, qkwargs=dict()):

    # FIRST workload including a model this execution
    if c.i == 1 and not mtask:
        if len(tasks) == 0:

            trajectories = sampling_function(project, engine, n_steps, n_traj)
            logger.info("Runtime new trajectories defined")

            if not c.done:
                logger.info("Converting trajectories to tasks")
                [tasks.append(t.run(**resource_requirements)) for t in trajectories]

                logger.info("Runtime new tasks queueing")
                queue_tasks(project, tasks, **qkwargs)

                c.increment()
                logger.info("Runtime new tasks queued")

            # wait for all initial trajs to finish ¿in this workload?
            waiting = True
            while waiting:
                # OK condition because we're in first
                #    extension, as long as its a fresh
                #    project.
                logger.debug("len(project.trajectories), n_traj: {0} {1}".format(
                    len(project.trajectories), n_traj
                ))

                if len(project.trajectories) >= n_traj - len(filter(lambda ta: ta.state in {'fail','cancelled'}, project.tasks)):
                    logger.info("adding first/next modeller task")
                    mtask = model_task(project, modeller, margs,
                        taskenv=taskenv, min_trajlength=min_model_trajlength,
                        resource_requirements=resource_requirements)
    
                    logger.info("\nQueued Modelling Task\nUsing these modeller arguments:\n" + pformat(margs))

                    tasks.extend(mtask)
                    waiting = False
                else:
                    time.sleep(3)

        return lambda: progress(tasks)

    # LAST workload in this execution
    elif c.i == c.n - 1:
        if len(tasks) < n_traj:
            if mtask:
            # breaking convention of mtask last
            # is OK because not looking for mtask
            # after last round, only task.done
                if mtask.is_done() and continuing:
                    mtask = model_task(project, modeller, margs,
                            taskenv=taskenv, min_trajlength=min_model_trajlength,
                            resource_requirements=resource_requirements)

                    tasks.extend(mtask)
                    logger.info("\nQueued Modelling Task\nUsing these modeller arguments:\n" + pformat(margs))
                
            logger.info("Project last tasks define")
            logger.info("Queueing final extensions after modelling done")
            logger.info("\nFirst MD Task Lengths: \n")

            trajectories = sampling_function(project, engine, n_steps, n_traj)

            [tasks.append(t.run(**resource_requirements)) for t in trajectories]

            logger.info("Project last tasks queue")
            if not c.done:

                logger.info("Queueing these: ")
                logger.info(tasks)
                queue_tasks(project, tasks, **qkwargs)

                c.increment()

            logger.info("Project last tasks queued")

        return lambda: progress(tasks)

    else:
        # MODEL TASK MAY NOT BE CREATED
        #  - timing is different
        #  - just running trajectories until
        #    prior model finishes, then starting
        #    round of modelled trajs along
        #    with mtask
        if len(tasks) == 0:
            logger.info("Queueing new round of modelled trajectories")
            logger.info("Project new tasks define")

            trajectories = sampling_function(project, engine, n_steps, n_traj)

            if not c.n or not c.done:
                [tasks.append(t.run(**resource_requirements)) for t in trajectories]
                logger.info("Project new tasks queue")

                queue_tasks(project, tasks, **qkwargs)

                c.increment()
                logger.info("Project new tasks queued")

                if mtask:
                    if mtask.is_done():
                        mtask = model_task(project, modeller, margs,
                                taskenv=taskenv, min_trajlength=min_model_trajlength,
                                resource_requirements=resource_requirements)

                        tasks.extend(mtask)

                return lambda: progress(tasks)

            else:
                return lambda: progress(tasks)

        else:
            return lambda: progress(tasks)
