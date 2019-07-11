
def calculate_request(size_workload, n_workloads, n_steps):
    '''
    Calculate the parameters for resource request.
    The workload to execute will be assessed to estimate these
    required parameters.
    -- Function in progress, also requires a minimum time
       and cpus per node. Need to decide how these will be
       calculated and managed in general.

    Parameters
    ----------
    size_workload : <int>
    For now, this is like the number of nodes that will be used.
    With OpenMM Simulations and the 1-node PyEMMA tasks, this is
    also the number of tasks per workload. Clearly a name conflict...

    n_workloads : <int>
    Number of workload iterations or rounds. The model here
    is that the workloads are approximately identical, maybe
    some will not include new modeller tasks but otherwise
    should be the same.

    n_steps : <int>
    Number of simulation steps in each task.

    steprate : <int>
    Number of simulation steps per minute. Use a low-side
    estimate to ensure jobs don't timeout before the tasks
    are completed.
    '''
    # TODO get this from the configuration and send to function
    rp_cpu_overhead = 16
    cpu_per_node = 16
    cpus = size_workload * cpu_per_node + rp_cpu_overhead
    # nodes is not used
    nodes = size_workload
    gpus = size_workload
    logger.info(formatline(
        "\nn_steps: {0}\nn_workloads: {1}\nsteprate: {2}".format(
                         n_steps, n_workloads, steprate)))

    return cpus, nodes, wallminutes, gpus
