
import subprocess
import shlex
import yaml
from string import Formatter

from pprint import pformat

from ..util import get_logger
logger = get_logger(__name__)

__all__ = ["create_request", "JobLauncher"]


cli_args_from_dict = lambda d: ' '.join(
    [' '.join([str(k),str(v)])
    for k,v in d.items() if v is not None])


def get_format_fields(s):
    fields = list()

    if isinstance(s, str):
        for result in Formatter().parse(s):

            if result[1]:
                fields.append(result[1])

    return fields


def flatten_list(l):
    '''Flatten nested lists
    down to the last turtle.
    '''
    return flatten_list(l[0]) + (
        flatten_list(l[1:]) if len(l) > 1 else []
    ) if type(l) is list else [l]


def isempty(l):
    '''Check if nested list structure is empty
    '''
    if isinstance(l, list):
        return all( map(isempty, l) )

    return False


def flatten_dict(d):
    def _flatten_dict(d):
        '''Sort-of Flatten nested dict
        They come out as nested lists
        '''
      #  if isinstance(d, list):
      #      for sub_d in d:
      #          yield list(_flatten_dict(sub_d))
        if isinstance(d, dict):
            for value in d.values():
                yield list(_flatten_dict(value))
        else:
            yield d

    result = list(map(lambda x: list(filter(lambda y: not isempty(y), x if isinstance(x, list) else [x])), _flatten_dict(d)))

    return result


def small_proc_watch_block(command):
    '''Should only use with fast executing commands
    and manageable output size. All errors are lost.
    '''
    proc = subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    out = proc.stdout.read()
    retval = proc.wait()

    return out, retval


class JobLauncher(object):
    '''Create an LRMS job to acquire resources for a workload.
    JobLauncher reads configuration from a yaml file. Two top-level
    fields are required: "workload" and "task". Options for each are
    built into the actual LRMS job.
    '''
    # set to False to get results without launch
    _live_ = True
    _required_ = {
        # FIXME go back to job for job stuff when
        #"job":  {"launcher"}, 
        "workload": {"command", "script"}, 
        "launch":   {"command"}, 
        #       renaming to fix workload name overload.
        #       task seems to be fine
        "task": {"main"},
    }

    def __init__(self):

        super(JobLauncher, self).__init__()

        self._job_launcher = None
        self._script = None
        self._keys = dict()
        self._job_configuration = dict()

    @property
    def ready(self):
        logger.debug(pformat(flatten_dict(list(filter(
            lambda k_v: "." not in k_v[0], self._keys.items())))))

        return all([
            v is not None for v
            in flatten_list(flatten_dict(list(filter(lambda k_v: "." not in k_v[0], self._keys.items()))))
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

    def _configure_job_launcher(self, job_path=None):
        self._job_script = (job_path + "/" if job_path else "") + "jobscript.bash"

        jobopts = self.job_configuration["workload"]
        job_launcher = jobopts["command"]
        job_launcher += " %s" % " ".join(jobopts.get("arguments", list()))
        job_launcher += " %s" % cli_args_from_dict(jobopts.get("options", dict()))

        self._job_launcher = ' '.join([job_launcher, self._job_script])

    def _configure_launcher(self, job_path=None):
        '''This is where the actual job script is built from a template
        '''

        if self._job_launcher:
            return

        if self.job_configuration:
            # FIXME a lot of craziness down there
            #       -- clarify types, required, sequence
            # TODO differentiate required vs optional
            #      config keys with 'get' vs hard hash
            self._configure_job_launcher(job_path)

            launchopts = self.job_configuration["launch"]
            launcher = launchopts["command"]
            launcher += " %s" % cli_args_from_dict(launchopts.get("resource", dict()))
            launcher += " %s" % " ".join(launchopts.get("arguments", list()))

            script_template = ""
            for line in self.job_configuration["workload"].get("script", list()):
                if isinstance(line, str):
                    script_template += "\n%s" % line

                elif isinstance(line, dict):
                    assert "task" in line
                    assert len(line) == 1

                    whichtask = line["task"]["name"]
                    taskopts = self.job_configuration["task"][whichtask]

                    task = ""
                    if "task." in launcher:
                        fields = {key:taskopts["launcher"][key] for key in  map(lambda k: "".join(k[1].split("task.")), filter(lambda k: bool(k[1]), Formatter().parse(launcher)))}
                        task += "".join(launcher.split("task.")).format(**fields)
                        logger.debug(task)

                    task += " %s" % taskopts["main"]["executable"]
                    task += " %s" % " ".join(taskopts["main"].get("arguments", list()))
                    task += " %s" % cli_args_from_dict(taskopts["main"].get("options", dict()))

                    script_template += "\n%s" % task

            self._script = script_template

    def load(self, cfg, require_on_load=False):
        if isinstance(cfg, str) and cfg.endswith(".yaml"):
            with open(yaml_config, 'r') as fyml:
                config = yaml.safe_load(fyml)

        elif isinstance(cfg, dict):
                config = cfg

        else:
            raise Exception("JobLauncher loads configuration from yaml file or dict")

        if require_on_load:
            # Should raise exception if not
            # all required fields filled
            self.check_ready_base(config)

        # FIXME recursive safe-update required here...
        for k,v in config.items():
            if k in self._job_configuration:
                if isinstance(self._job_configuration[k], dict):
                    self._job_configuration[k].update(v)
                else:
                    logger.warning(
                        "Field '%s' showed up in multiple config components"
                         % k)

            else:
                if v:
                    self._job_configuration[k] = v
                else:
                    logger.warning(
                        "Field '%s' was empty not added to config"
                         % k)

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

        for k in config_dict:
            if k in self._keys:
                if not self._keys[k]:
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

        with open(self._job_script, 'w') as fjob:
            fjob.write("#!/bin/bash\n")
            fjob.write(script)

    def _fill_fields(self, template):
        needed_keys = get_format_fields(template)
        logger.debug(template)
        kwargs = dict()
        [kwargs.update({k:self._keys[k]}) for k in needed_keys]
        filled = template.format(**kwargs)

        return filled

    def launch_job(self, job_path=None):
        '''Launch a job using the built command
        if the configuration is complete, ie keys
        all have values.
        '''

        if self.ready:
            #if not self.job_launcher:
            logger.debug("Using job_path: %s" % job_path)
            self._configure_launcher(job_path)

            job_launcher = self._fill_fields(self.job_launcher)

            logger.info("Job Launcher")
            logger.info(" -- " + job_launcher)
            if self.__class__._live_:
                self._write_script()

                out, retval = small_proc_watch_block(
                   job_launcher)

                # FIXME confusing stdout with returncode i think
                logger.info(out)
                logger.info("")
                logger.info(
                    "Any errors during submission? (0 means no, i.e. good thing)")
                logger.info(retval)
                logger.info("")

            else:
                logger.info("Not launching now")

        else:
            logger.warning(
                "Job is not fully configured, here are the current key fields")
            logger.warning(self._keys)


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
