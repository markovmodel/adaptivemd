
import os
import sys
import yaml
#from pprint import pformat
#import uuid
#import time

from .control import queue_tasks, all_done
from .util import counter

from ..sampling import get_sampling_function
from ..util import get_logger
logger = get_logger(__name__)


__all__ = ["workflow_generator_simple", "model_extend_simple"]


def workflow_generator_simple(
    project, engine, n_run, n_ext, n_steps, round_n,
    longest = 5000,
    n_rounds = 0,
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
    min_model_trajlength = 0,
    sampling_function_name = 'explore_macrostates',

    # these arent currently utilized
    mpi_rank = 0,
    randomly = False,
    margs_file = None,
    continuing = True,
    **kwargs,):

    logger.info("Starting workflow_generator_simple function")
    sampling_function = get_sampling_function(
        sampling_function_name, **sfkwargs
    )

    resource_requirements = dict() # TODO calculate request

    if progression == 'all':
        progress = lambda tasks: all([ta.is_done() for ta in tasks])

    else:
        progress = lambda tasks: any([ta.is_done() for ta in tasks])

    c = counter(n_rounds)
    tasks = list()

    if n_rounds:

        assert isinstance(n_rounds, int)
        assert n_rounds > 0

        logger.info("Going to do n_rounds:  {}".format(c.n))

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

        for traj in project.new_trajectory(engine['pdb_file'], n_steps, engine, n_run):
            tasks.append(traj.run(**resource_requirements))
            if admd_profile: # This should be path to an RC file
                tasks[-1].pre.insert(0, "source %s" % admd_profile)

        if not n_rounds or not c.done:
            logger.info("Project first tasks queue")
            queue_tasks(project, tasks, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)
            c.increment()

        logger.info("Project first tasks queued")
        logger.info("Queued First Tasks in new project")

        yield lambda: progress(tasks)

        logger.info("First Tasks are done")
        logger.info("Project first tasks done")

    else:

        notfirsttime = True

    c_ext = 0
    mtask = None

    with open(margs_file, 'r') as f:
        _margs = yaml.safe_load(f)

    margs = lambda rn: _margs[max(list(filter(lambda mi: mi <= rn, _margs)))]

    # Start of CONTROL LOOP
    # when on final workload, with c_ext == n_ext,
    while c_ext <= n_ext and (not n_rounds or not c.done):

        logger.info("Checking Extension Lengths")

        done = False
        lastcheck = True
        priorext = 0
        # TODO fix, this isn't a consistent name "trajectories"
        trajectories = set()
        while not done and ( not n_rounds or not c.done ):

            #print("looking for too-short trajectories")
            if c.done:
                xtasks = list()
            else:
                #logger.info(formatline("TIMER Brain ext tasks define {0:.5f}".format(time.time())))
                #active_trajs =  ~~~  after_n_trajs_trajs
                after_n_trajs_trajs = list(project.trajectories.sorted(lambda tj: tj.__time__))[startontraj:]
                logger.info("Checking last {} trajectories for proper length".format(len(after_n_trajs_trajs)))
                xtasks = check_trajectory_minlength(project, minlength, n_steps, n_run, task_env=taskenv,
                    trajectories=after_n_trajs_trajs, resource_requirements=resource_requirements)
                   # environment=environment,
                   # activate_prefix=activate_prefix, virtualenv=virtualenv,
                   # task_env=task_env, resource_requirements=resource_requirements)

            tnames = set()
            if len(trajectories) > 0:
                [tnames.add(_) for _ in set(zip(*trajectories)[0])]

            #if xtasks:
            #    logger.info(formatline("TIMER Brain ext tasks queue {0:.5f}".format(time.time())))
            queuethese = list()
            for xta in xtasks:
                tname = xta.trajectory.basename

                if tname not in tnames:
                    tnames.add(tname)
                    trajectories.add( (tname, xta) )
                    queuethese.append(xta)

            queue_tasks(project, queuethese, rp_client, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

            #if xtasks:
            #    logger.info(formatline("TIMER Brain ext tasks queued {0:.5f}".format(time.time())))
            removals = list()
            for tname, xta in trajectories:
                if xta.state in {"fail","halted","success","cancelled"}:
                    removals.append( (tname, xta) )

            for removal in removals:
                trajectories.remove(removal)

            if len(trajectories) == n_run and priorext < n_run:
                logger.info("Have full width of extensions")
                c.increment()

            # setting this to look at next round
            priorext = len(trajectories)

            if len(trajectories) == 0:
                if lastcheck:
                    logger.info("Extensions last check")
                    lastcheck = False
                    time.sleep(15)

                else:
                    logger.info("Extensions are done")
                    #logger.info(formatline("TIMER Brain ext tasks done {0:.5f}".format(time.time())))
                    done = True

            else:
                if not lastcheck:
                    lastcheck = True

                time.sleep(15)

        logger.info("----------- Extension #{0}".format(c_ext))

        # when c_ext == n_ext, we just wanted
        # to use check_trajectory_minlength above
        if c_ext < n_ext and not c.done:
            logger.info(formatline("TIMER Brain main loop enter {0:.5f}".format(time.time())))
            tasks = list()
            if not modeller:
                c_ext += 1
                logger.info("Extending project without modeller")
                yield lambda: model_extend(modeller, randbreak, c=c)
                logger.info(formatline("TIMER Brain main no modeller done {0:.5f}".format(time.time())))
            else:
                margs = update_margs(_margs, round_n)

                logger.info("Extending project with modeller")
                logger.info("margs for this round will be: {}".format(pformat(margs)))

                if mtask is None:

                    mtime -= time.time()
                    yield lambda: model_extend(modeller, randbreak, c=c)

                    logger.info(formatline("TIMER Brain main loop1 done {0:.5f}".format(time.time())))
                    logger.info("Set a current modelling task")
                    mtask = tasks[-1]
                    logger.info("First model task is: {}".format(mtask))

                # TODO don't assume mtask not None means it
                #      has is_done method. outer loop needs
                #      upgrade
                elif mtask.is_done():

                    mtime += time.time()
                    mtimes.append(mtime)
                    mtime = -time.time()
                    logger.info("Current modelling task is done")
                    logger.info("It took {0} seconds".format(mtimes[-1]))
                    c_ext += 1

                    yield lambda: model_extend(modeller, randbreak, mtask, c=c)
                    logger.info(formatline("TIMER Brain main loop2 done {0:.5f}".format(time.time())))

                    pythontask_callback(mtask, scd)
                    #mpath = os.path.expandvars(mtask.__dict__['post'][1].target.url.replace('project:///','$ADMDRP_DATA/projects/{}/'.format(project.name)))
                    #mtask._cb_success(scd, mpath)
                    logger.info("Added another model to project, now have: {}".format(len(project.models)))

                    print_last_model(project)
                    mtask = tasks[-1]
                    logger.info("Set a new current modelling task")

                elif not mtask.is_done():
                    logger.info("Continuing trajectory tasks, waiting on model")
                    yield lambda: model_extend(modeller, randbreak, mtask, c=c)
                    logger.info(formatline("TIMER Brain main loop3 done {0:.5f}".format(time.time())))

                else:
                    logger.info("Not sure how we got here")
                    pass


        # End of CONTROL LOOP
        # need to increment c_ext to exit the loop
        else:
            c_ext += 1



def model_extend_simple(modeller, c_ext, tasks, n_steps, sampling_function, mtask=None, c=None):
    #print("c_ext is ", c_ext, "({0})".format(n_ext))
    #print("length of extended is: ", len(extended))

    # FIRST workload including a model this execution
    if c_ext == 0:
        if len(tasks) == 0:

            trajectories = sampling_function(project, engine, n_steps, n_run)
            logger.info("Runtime new trajectories defined")

            if not n_rounds or not c.done:
                logger.info("Converting trajectories to tasks")
                [tasks.append(t.run(**resource_requirements)) for t in trajectories]

                logger.info("Runtime new tasks queueing {0:.5f}".format(time.time()))
                queue_tasks(project, tasks, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

                c.increment()
                logger.info("Runtime new tasks queued")

            # wait for all initial trajs to finish ¿in this workload?
            waiting = True
            while waiting:
                # OK condition because we're in first
                #    extension, as long as its a fresh
                #    project.
                logger.debug("len(project.trajectories), n_run: {0} {1}".format(
                    len(project.trajectories), n_run
                ))

                if notfirsttime or len(project.trajectories) >= n_run - len(filter(lambda ta: ta.state in {'fail','cancelled'}, project.tasks)):
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
    elif c_ext == n_ext:
        if len(tasks) < n_run:
            if mtask:
            # breaking convention of mtask last
            # is OK because not looking for mtask
            # after last round, only task.done
                if mtask.is_done() and continuing:
                    mtask = model_task(project, modeller, margs,
                            taskenv=taskenv, rp_client=rp_client, min_trajlength=min_model_trajlength,
                            resource_requirements=resource_requirements)

                    tasks.extend(mtask)
                    logger.info("\nQueued Modelling Task\nUsing these modeller arguments:\n" + pformat(margs))
                
            logger.info("Project last tasks define")
            logger.info("Queueing final extensions after modelling done")
            logger.info("\nFirst MD Task Lengths: \n")

            trajectories = sampling_function(project, engine, unrandbreak, n_run)

            [tasks.append(t.run(**resource_requirements)) for t in trajectories]
            add_task_env(tasks, **taskenv)

            logger.info("Project last tasks queue")
            if not n_rounds or not c.done:

                logger.info("Queueing these: ")
                logger.info(tasks)
                queue_tasks(project, tasks, rp_client, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

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

            trajectories = sampling_function(project, engine, n_steps, n_run)

            if not n_rounds or not c.done:
                [tasks.append(t.run(**resource_requirements)) for t in trajectories]
                add_task_env(tasks, **taskenv)
                logger.info("Project new tasks queue")

                queue_tasks(project, tasks, rp_client, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

                c.increment()
                logger.info("Project new tasks queued")

                if mtask:
                    if mtask.is_done():
                        mtask = model_task(project, modeller, margs,
                                taskenv=taskenv, rp_client=rp_client, min_trajlength=min_model_trajlength,
                                resource_requirements=resource_requirements)

                        tasks.extend(mtask)

                return lambda: progress(tasks)

            else:
                return lambda: progress(tasks)

        else:
            return lambda: progress(tasks)
