from adaptivemd import PythonTask
from adaptivemd.analysis import Analysis
from _remote import remote_analysis


class PyEMMAAnalysis(Analysis):
    """
    Common computation of correlations between features using PyEmma

    Attributes
    ----------
    pdb_file : `File`
        file reference to the pdb_file for reference topology
    """

    def __init__(self, pdb_file):
        super(PyEMMAAnalysis, self).__init__()

        self['pdb_file'] = pdb_file
        stage = pdb_file.transfer('staging:///')

        self['pdb_file_stage'] = stage.target
        self.initial_staging.append(stage)

    @staticmethod
    def then_func(project, task, model, inputs):
        # add the input arguments for later reference
        model.data['input']['trajectories'] = inputs['trajectories']
        model.data['input']['pdb'] = inputs['topfile']
        project.models.add(model)

    def task_run_msm_files(
            self,
            trajectories,
            outtype='master',
            tica_lag=2,
            tica_dim=2,
            msm_states=5,
            msm_lag=2,
            stride=1):
        """
        Create a task that computes an msm using a given set of trajectories

        Parameters
        ----------
        trajectories : list of `Trajectory`
            the list of trajectory references to be used in the computation
        outtype : str
            name of the output description to pick the frames from
        tica_lag : int
            the lag-time used for tCIA
        tica_dim : int
            number of dimensions using in tICA. This refers to the number of tIC used
        msm_states : int
            number of micro-states used for the MSM
        msm_lag : int
            lagtime used for the MSM construction
        stride : int
            a stride to be used on the data. Can speed up computation at reduced accuracy

        Returns
        -------
        `Task`
            a task object describing a simple python RPC call using pyemma

        """

        # we call the PythonTask with self to tell him about the generator used
        # this will fire the then_func from the generator once finished
        t = PythonTask(self)

        input_pdb = t.link(self['pdb_file_stage'], 'input.pdb')

        trajs = list(trajectories)

        if len(trajs) == 0:
            # nothing to analyze
            return

        for t in trajs:
            if outtype not in t.types:
                # ups, one of the trajectories does not have the required type!
                return

        ty = trajs[0].types[outtype]

        t.call(
            remote_analysis,
            trajectories=trajs,
            traj_name=ty.filename,  # we need the filename in the traj folder
            topfile=input_pdb,
            tica_lag=tica_lag,
            tica_dim=tica_dim,
            msm_states=msm_states,
            msm_lag=msm_lag,
            stride=stride
        )

        return t
