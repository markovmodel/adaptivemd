
import os
import sys
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
    read_margs = True,
    continuing = True,
    gpu_contexts = 1,
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
