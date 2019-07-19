

import os
import sys
#from pprint import pformat
#import uuid
#import time

from .control import queue_tasks, all_done
from .util import add_task_env

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


    sampling_function = get_sampling_function(
        sampling_function_name, **sfkwargs
    )

    return True


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
                add_task_env(tasks, **taskenv)

                logger.info("Runtime new tasks queueing {0:.5f}".format(time.time()))
                queue_tasks(project, tasks, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

                c.increment()
                logger.info("Runtime new tasks queued")

            # wait for all initial trajs to finish
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
    
                    logger.info(formatline("\nQueued Modelling Task\nUsing these modeller arguments:\n" + pformat(margs)))

                    tasks.extend(mtask)
                    waiting = False
                else:
                    time.sleep(3)

        #print(tasks)
        #print("First Extensions' status':\n", [ta.state for ta in tasks])

        return lambda: progress(tasks)
        #return any([ta.is_done() for ta in tasks[:-1]])
        #return lambda: len(filter(lambda ta: ta.is_done(), tasks)) > len(tasks) / 2
        #return all([ta.is_done() for ta in tasks[:-1]])

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
                    logger.info(formatline("\nQueued Modelling Task\nUsing these modeller arguments:\n" + pformat(margs)))
                
            logger.info(formatline("TIMER Brain last tasks define {0:.5f}".format(time.time())))
            logger.info("Queueing final extensions after modelling done")
            logger.info(formatline("\nFirst MD Task Lengths: \n".format(randbreak)))
            unrandbreak = [2*n_steps - rb for rb in randbreak]
            unrandbreak.sort()
            unrandbreak.reverse()
            logger.info(formatline("\nFinal MD Task Lengths: \n".format(unrandbreak)))

            trajectories = sampling_function(project, engine, unrandbreak, n_run)
            #trajectories = project.new_ml_trajectory(engine, unrandbreak, n_run)
            #trajectories = [project.new_trajectory(engine['pdb_file'], urb, engine) for urb in unrandbreak]

            [tasks.append(t.run(**resource_requirements)) for t in trajectories]
            #add_task_env(tasks, environment, activate_prefix, virtualenv, task_env, pre=pre_cmds)
            add_task_env(tasks, **taskenv)

            logger.info(formatline("TIMER Brain last tasks queue {0:.5f}".format(time.time())))
            if not n_rounds or not c.done:

                logger.info("Queueing these: ")
                logger.info(tasks)
                queue_tasks(project, tasks, rp_client, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

                c.increment()

            logger.info(formatline("TIMER Brain last tasks queued {0:.5f}".format(time.time())))

        return lambda: progress(tasks)
        #return any([ta.is_done() for ta in tasks])
        #return lambda: len(filter(lambda ta: ta.is_done(), tasks)) > len(tasks) / 2
        #return all([ta.is_done() for ta in tasks])

    else:
        # MODEL TASK MAY NOT BE CREATED
        #  - timing is different
        #  - just running trajectories until
        #    prior model finishes, then starting
        #    round of modelled trajs along
        #    with mtask
        if len(tasks) == 0:
            logger.info("Queueing new round of modelled trajectories")
            logger.info(formatline("TIMER Brain new tasks define {0:.5f}".format(time.time())))

            trajectories = sampling_function(project, engine, n_steps, n_run)
            #trajectories = project.new_ml_trajectory(engine, n_steps, n_run)
            #trajectories = [project.new_trajectory(engine['pdb_file'], n_steps, engine) for _ in range(n_run)]

            if not n_rounds or not c.done:
                [tasks.append(t.run(**resource_requirements)) for t in trajectories]
                #add_task_env(tasks, environment, activate_prefix, virtualenv, task_env, pre=pre_cmds)
                add_task_env(tasks, **taskenv)
                logger.info(formatline("TIMER Brain new tasks queue {0:.5f}".format(time.time())))

                queue_tasks(project, tasks, rp_client, sleeptime=batchsleep, batchsize=batchsize, wait=batchwait)

                c.increment()
                logger.info(formatline("TIMER Brain new tasks queued {0:.5f}".format(time.time())))

                if mtask:
                    if mtask.is_done():
                        mtask = model_task(project, modeller, margs,
                                taskenv=taskenv, rp_client=rp_client, min_trajlength=min_model_trajlength,
                                resource_requirements=resource_requirements)

                        tasks.extend(mtask)

                return lambda: progress(tasks)
                #return any([ta.is_done() for ta in tasks[:-1]])
                #return lambda: len(filter(lambda ta: ta.is_done(), tasks)) > len(tasks) / 2
                #return all([ta.is_done() for ta in tasks[:-1]])

            else:
                return lambda: progress(tasks)
                #return any([ta.is_done() for ta in tasks])
                #return lambda: len(filter(lambda ta: ta.is_done(), tasks)) > len(tasks) / 2
                #return all([ta.is_done() for ta in tasks])

        else:
            return lambda: progress(tasks)
            #return any([ta.is_done() for ta in tasks])
            #return lambda: len(filter(lambda ta: ta.is_done(), tasks)) > len(tasks) / 2
            #return all([ta.is_done() for ta in tasks])
