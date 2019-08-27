


import os
from time import sleep

from pprint import pformat

from .jobs import JobLauncher
from ..util import get_logger

logger = get_logger(__name__)



def check_trajectory_minlength(project, minlength, trajectories, n_steps, n_traj=0,
                               resource_requirements=None, **kwargs):

    #if not trajectories:
    #    trajectories = project.trajectories

    tasks = list()
    for t in trajectories:

        tlength = t.length
        xlength = 0

        if tlength < minlength:
            if minlength - tlength > n_steps:
                xlength += n_steps
            else:
                xlength += minlength - tlength

        if xlength:
            tasks.append(t.extend(xlength, **resource_requirements))

    if n_traj is not None and len(tasks) > n_traj:
        tasks = tasks[:n_traj]

    return tasks


def create_workload_launcher(project, workload, session, args, cwd):

    os.makedirs(os.path.join(session, "workers"))

    job_state_filename = "admd.job.state"
    js = os.path.join(session, job_state_filename)
    with open(js, "w") as f: f.write("UNLAUNCHED")
    n_tasks  = len(workload)
    # FIXME inflexible, assumes 1 database node and homogenous tasks currently
    n_nodes  = 1 + n_tasks // project.configuration.task["worker"]["launcher"]["tasks_per_node"] + bool(
        n_tasks % project.configuration.task["worker"]["launcher"]["tasks_per_node"]
    )

    # For scaled tasks
    cpu_per_task = project.configuration.resource["cpu_per_node"] // project.configuration.task["worker"]["launcher"]["tasks_per_node"]

    walltime = args.minutes

    jl = JobLauncher()

    jl.load({"workload": project.configuration.workload})
    jl.load({"launch":   project.configuration.launch})
    jl.load({"task":     project.configuration.task})
    logger.debug(pformat(jl._keys))

    #jobconfig = process_resource_config(project.configuration)
    jobconfig = dict()
    jobconfig["job_name"]     = "admd"
    jobconfig["job_state"]    = job_state_filename
    jobconfig["job_home"]     = os.path.join(cwd, session)
    jobconfig["minutes"]      = args.minutes
    jobconfig["n_nodes"]      = n_nodes
    jobconfig["n_tasks"]      = n_tasks
    jobconfig["project_name"] = project.name
    jobconfig["admd_dburl"]   = "$ADMD_DBURL"
    jobconfig["admd_profile"] = args.rc
    jobconfig["dbhome"]       = os.path.join(cwd, "mongo")
    jobconfig["dbport"]       = 27017
    jobconfig["netdevice"]    = project.configuration.resource["netdevice"]
    jobconfig["queue"]        = project.configuration.resource["queue"]
    jobconfig["cpu_per_node"] = project.configuration.resource["cpu_per_node"]
    jobconfig["cpu_per_task"] = cpu_per_task
    jobconfig["gpu_per_node"] = project.configuration.resource["gpu_per_node"]
    jobconfig["allocation"]   = project.configuration.user["allocation"]

    jl.configure_workload(jobconfig)
    logger.debug(pformat(jl._keys))

    # TODO attach resource acquisition and config at project level
    project.request_resource(walltime, n_nodes)
    logger.info(
        "\nResource requested:\nnodes: {0}\nwalltime: {1}\n".format(
        n_nodes, walltime)
    )

    return jl


def queue_tasks(project, tasks, wait=False, batchsize=9999999, sleeptime=5):
    # TODO this belongs in the project queue method
    '''This function queues tasks to a `Project` instance in batches.
    For high-scale workflows with thousands to tens of thousands of
    tasks, it may be beneficial to introduce some additional control
    rather than submitting all tasks for a workload in bulk. 

    Arguments
    ---------
    project :: `adaptivemd.Project`
    the instance where new tasks will be queued

    tasks :: ``
    the complete group of new tasks to queue

    wait :: `False`, `"any"`, `"all"`
    if `"any"` or `"all"`, the next batch will wait for either
    any or all tasks in prior batch to change to `running` state 
    before queueing the next batch

    batchsize :: `int`
    the number of tasks queued at a time to the `Project`

    sleeptime :: `int`
    the waiting time between task state checks of previous batch
    '''
    logger.debug("Arguments to task queueing function")

    logger.debug("wait={w} batchsize={b} sleeptime={s}".format(
           w=wait, b=batchsize, s=sleeptime)
    )

    for i in range( len(tasks) // batchsize + bool(len(tasks) % batchsize) ):
        waiting = False

        if wait:
            waiting = True

            if wait == 'any':
                waitfunc = any

            elif wait == 'all':
                waitfunc = all

            else:
                raise ValueError("Wait argument must be 'any' or 'all' if given")

        _tasks = tasks[ i*batchsize : (i+1)*batchsize ]

        if _tasks:

            logger.debug("Queueing these tasks: {}".format(tasks))
            project.queue(_tasks)
            sleep(sleeptime)

            while waiting:
                logger.debug("waiting: ", waitfunc, _tasks)

                if waitfunc(map(lambda ta: ta.state in {'running','cancelled','success'}, _tasks)):
                    logger.debug("Done waiting: {} have progressed".format(waitfunc))
                    waiting = False

                else:

                    logger.debug("Waiting")
                    logger.debug(reduce(lambda s,ta: s+' '+ta.state, [' ']+list(_tasks)))
                    logger.debug("Sleeping for {} seconds".format(sleeptime))

                    sleep(sleeptime)

