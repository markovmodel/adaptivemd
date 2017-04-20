from __future__ import absolute_import, print_function

from adaptivemd.scheduler import Scheduler
from adaptivemd.resource import Resource

from .scheduler import RPScheduler


class RPCluster(Resource):
    def __init__(self, shared_path=None, path_to_conda=None,
                 access_schema=None, exit_on_error=True, project=None):
        super(RPCluster, self).__init__(shared_path)
        self.path_to_conda = path_to_conda
        self.access_schema = access_schema
        self.exit_on_error = exit_on_error
        self.project = project

    # allow to change the working dir?
    # def __init__(self, path_to_cond=None, working_dir=None):
    #     session = rp.Session()
    #     cfg = session.get_resource_config(RESOURCE)
    #     new_cfg = rp.ResourceConfig(RESOURCE, cfg)
    #     new_cfg.default_remote_workdir = work_dir
    #     session.add_resource_config(new_cfg)

    def scheduler(self, queue, runtime, cores, rp_resource=None):
        """
        `Scheduler` generator

        Parameters
        ----------
        queue : str or None
            name of the queue to be used
        runtime : int
            maximal walltime in minutes
        cores : int
            cores to be used
        rp_resource : str
            if set this will override the default resource for the scheduler

        Returns
        -------
        `Scheduler`
            the scheduler object representing a cluster attached to the resource
        """
        sc = RPScheduler(
            resource=self.resource,
            queue=queue,
            runtime=runtime,
            cores=cores,
            rp_resource=rp_resource)

        if self.resource.path_to_conda:
            sc.wrapper.add_path(self.resource.path_to_conda)

        return sc

    def default(self):
        """
        Return the default scheduler

        Returns
        -------
        `Scheduler`
        """
        return self.scheduler(None, 150, 2)


class RPAllegroCluster(RPCluster):
    def __init__(self, path_to_conda=None,
                 access_schema='ssh', exit_on_error=True, project=None):
        super(RPAllegroCluster, self).__init__(
            '$HOME/NO_BACKUP/radical.pilot.sandbox/',
            path_to_conda,
            access_schema,
            exit_on_error,
            project)

    def scheduler(self, queue, runtime, cores, rp_resource=None):
        sc = super(RPAllegroCluster, self).scheduler(
            queue, runtime, cores, rp_resource)

        return sc

    def cpu(self, runtime=150, cores=2):
        """
        Return a CPU _big_ queue on Allegro

        Parameters
        ----------
        runtime : int
            maximal walltime in minutes
        cores : int
            cores to be used

        Returns
        -------
        `Scheduler`
        """
        return self.scheduler('big', runtime, cores, rp_resource='fub.allegro')

    def gpu(self, runtime=150):
        """
        Return a GPU _gpu_ queue on Allegro

        Notes
        -----
        This takes care that the CUDA 7.5 module is loaded

        Parameters
        ----------
        runtime : int
            maximal wall time in minutes

        Returns
        -------
        `Scheduler`
        """
        sc = self.scheduler('gpu', runtime, 8, rp_resource='fub.allegro')
        w = sc.wrapper
        w.append(
            'export MODULEPATH=/import/ag_cmb/software/modules:$MODULEPATH')
        w.append('module load cuda/7.5')
        return sc

    def default(self):
        return self.cpu()


class RPLocalCluster(RPCluster):
    def __init__(self, path_to_conda=None,
                 access_schema='local', exit_on_error=True, project=None):
        super(RPLocalCluster, self).__init__(
            '$HOME/radical.pilot.sandbox/',
            path_to_conda,
            access_schema,
            exit_on_error,
            project)

    def scheduler(self, queue, runtime, cores, rp_resource=None):
        sc = super(RPLocalCluster, self).scheduler(queue, runtime, cores, 'local.localhost')
        return sc
