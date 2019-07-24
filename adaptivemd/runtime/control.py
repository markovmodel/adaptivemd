


from time import sleep

from ..util import get_logger

logger = get_logger(__name__)


def all_done(tasks):
        '''Check if a workload (batch of tasks) is done
        '''         
        # TODO establish / utilize FINAL_STATES via adaptivemd.Task class
        logger.info("Checking if all done")
        idle_time = 5

        n_waiting = len(tasks) - len(filter(
            lambda ta: ta.state in {'dummy','cancelled', 'fail', 'success'},
            project.tasks
        ))

        if n_waiting > 0:

            logger.info("Waiting on {} tasks".format(n_waiting))
            sleep(idle_time)

            return False

        else:

            logger.info("All Tasks in Final States")

            return True


def queue_tasks(project, tasks, wait=False, batchsize=9999999, sleeptime=5):
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
    logger.info("Arguments to task queueing function")

    logger.info("wait={w} batchsize={b} sleeptime={s}".format(
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

            logger.debug("Queueing these tasks: {}".format_tasks))
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

