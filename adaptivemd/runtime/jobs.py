
__all__ = ["create_request", "JobLauncher"]


class JobLauncher(object):
    '''Create an LRMS job to acquire resources for a workload.
    JobBuilder reads configuration from a yaml file. Two top-level
    fields are required: "workload" and "task". Options for each are
    built into the actual LRMS job.
    '''
    # set to False to get results without launch
    _live_ = True
    _required_ = {
        # FIXME go back to job for job stuff when
        #"job":  {"launcher"}, 
        "workload":  {"launcher"}, 
        #       renaming to fix workload name overload.
        #       task seems to be fine
        "task": {"launcher","resource","main"},
    }

    def __init__(self):

        super(JobBuilder, self).__init__()

        self._job_launcher = None
        self._script = None
        self._keys = dict()
        self._job_configuration = dict()

    @property
    def ready(self):
        return all([
            v is not None for v
            in flatten_list(flatten_dict(self._keys))
        ])

    @property
    def job_configuration(self):
        return self._job_configuration

    @property
    def job_launcher(self):
        '''Job submission CLI command
        that is actually used to submit a job
        to the LRMS.
        '''
        if self._job_launcher is None:
            if self.job_configuration is not None:
                self._configure_launcher()

        return self._job_launcher

    def _configure_launcher(self):

        if self._job_launcher:
            return

        if self.job_configuration:
            # FIXME a lot of craziness down there
            #       -- clarify types, required, sequence
            # TODO differentiate required vs optional
            #      config keys with 'get' vs hard hash
            jobopts = self.job_configuration["workload"]
            launcher = jobopts["launcher"]
            launch_args = ' '.join(jobopts["arguments"])
            launch_opts = cli_args_from_dict(jobopts["options"])

            job_launcher = ' '.join(
                [launcher, launch_args, launch_opts])

            job_script = "jobscript.bash"
            self._job_launcher = ' '.join([job_launcher, job_script])

            taskopts = self.job_configuration["task"]

            launcher = taskopts["launcher"]
            launch_args = cli_args_from_dict(taskopts["resource"])
            task_launcher = ' '.join([launcher, launch_args])

            main_exec = taskopts["main"]["executable"][0]
            main_args = ' '.join(taskopts["main"]["arguments"])
            main_opts = taskopts["main"].get("options", "")

            if main_opts is None:
                main_opts = ""
            else:
                main_opts = cli_args_from_dict(main_opts)

            task = '\n'.join([
                ' '.join([task_launcher, main_exec, main_args, main_opts]),
            ])

            script_template = '\n'.join(
                self.job_configuration["workload"]["script"])

            postscript_template = '\n'.join(
                self.job_configuration["workload"]["postscript"])

            self._script = '\n\n'.join(
                [script_template, task, postscript_template])

    def load(self, yaml_config, require_on_load=False):

        with open(yaml_config, 'r') as fyml:
            config = yaml.safe_load(fyml)

        if require_on_load:
            # Should raise exception if not
            # all required fields filled
            self.check_ready_base(config)

        # FIXME recursive safe-update required here...
        for k,v in config.items():
            if k in self._job_configuration:
                self._job_configuration[k].update(v)
            else:
                self._job_configuration[k] = v

        self._read_config_keys()

    def check_ready_base(self, config=None):

        if config is None:
            config = self._job_configuration

        for r in self.__class__._required_:

            try:
                assert r in config
                assert all([
                    _r in config[r] for _r
                    in self.__class__._required_[r]
                ])

            except AssertionError as ae:
                print("Missing a required value or subconfig for: '%s'" % r)
                print("from the config file: '%s'" % yaml_config)
                raise ae

    def configure_workload(self, config_dict):
        '''Give a configuration to bind missing parameters.
        If all parameter keys are given values, the `ready`
        attribute will return True and jobs can be launched.
        '''
        assert isinstance(config_dict, dict)

        for k in self._keys:
            self._keys[k] = config_dict[k]

    def _read_config_keys(self):
        '''Keys allow user to hook parameters later
        such as the walltime, number of nodes, etc.
        '''
        flatconfig = flatten_list(flatten_dict(
            self.job_configuration))

        format_fields = [
            k for fc in flatconfig if isinstance(fc, str) 
            for k in get_format_fields(fc)
        ]

        newkeys = {
            k:None for k in format_fields
        }

        self._keys.update(newkeys)

    def _write_script(self):
        '''Write a script to submit a job
        '''
        script = self._fill_fields(self._script)

        with open('jobscript.bash', 'w') as fjob:
            fjob.write("#!/bin/bash\n")
            fjob.write(script)

    def _fill_fields(self, template):
        needed_keys = get_format_fields(template)
        kwargs = dict()
        [kwargs.update({k:self._keys[k]}) for k in needed_keys]
        filled = template.format(**kwargs)

        return filled

    def launch_job(self):
        '''Launch a job using the built command
        if the configuration is complete, ie keys
        all have values.
        '''

        if self.ready:
            if not self.job_launcher:
                self._configure_launcher()

            job_launcher = self._fill_fields(self.job_launcher)

            print("Job Launcher")
            print(" -- " + job_launcher)
            if self.__class__._live_:
                self._write_script()

                out, retval = small_proc_watch_block(
                   job_launcher)

                # FIXME confusing stdout with returncode i think
                print(out)
                print("")
                print("Any errors during submission? (0 means no, i.e. good thing)")
                print(retval)
                print("")

            else:
                print("Not launching now")


# TODO delete or make useful
def create_request(size_workload, n_workloads, n_steps):
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
