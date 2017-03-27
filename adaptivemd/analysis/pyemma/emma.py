from adaptivemd import PythonTask
from adaptivemd.analysis import Analysis
from _remote import remote_analysis


class PyEMMAAnalysis(Analysis):
    """
    Common computation of correlations between features using PyEmma

    Attributes
    ----------
    engine : `Engine`
        reference to an engine that knows about the topology
    outtype : str
        name of the output description to pick the frames from
    features : dict or list or None
        a feature descriptor in the format. A dict has exactly one entry:
        functionname: [attr1, attr2, ...]. attributes can be results of
        function calls. All function calls are to the featurizer object!
        If a list is given each element is considered to be a feature
        descriptor. If None (default) all coordinates will be added as
        features (.add_all())

        Examples

            {'add_backbone_torsions': None}          -> feat.add_backbone_torsions()
            {'add_distances': [ [[0,10], [2,20]] ]}  -> feat.add_distances([[0,10], [2,20]])
            {'add_inverse_distances': [
                { 'select_backbone': None } ]}       -> feat.add_inverse_distances(select_backbone())
    """

    def __init__(self, engine, outtype='master', features=None):

        super(PyEMMAAnalysis, self).__init__()

        pdb_file = engine['pdb_file']

        # todo: reuse the engines staged pdb_file if possible

        self['pdb_file'] = pdb_file
        stage = pdb_file.transfer('staging:///')

        self['pdb_file_stage'] = stage.target
        self.initial_staging.append(stage)

        self.outtype = outtype
        self.engine = engine
        self.features = features

    @classmethod
    def from_dict(cls, dct):
        obj = super(Analysis, cls).from_dict(dct)
        for k in ['outtype', 'engine', 'features']:
            setattr(obj, k, dct[k])

        return obj

    def to_dict(self):
        dct = super(Analysis, self).to_dict()
        for k in ['outtype', 'engine', 'features']:
            dct[k] = getattr(self, k)
        return dct

    @staticmethod
    def then_func(project, task, model, inputs):
        # add the input arguments for later reference
        model.data['input']['trajectories'] = inputs['trajectories']
        model.data['input']['pdb'] = inputs['topfile']

        # from the task we get the used generator and then its outtype
        model.data['input']['modeller'] = task.generator
        project.models.add(model)

    def execute(
            self,
            trajectories,
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

        outtype = self.outtype
        features = self.features

        for traj in trajs:
            if outtype not in traj.types:
                # ups, one of the trajectories does not have the required type!
                return

        ty = trajs[0].types[outtype]

        t.call(
            remote_analysis,
            trajectories=trajs,
            traj_name=ty.filename,  # we need the filename in the traj folder
            selection=ty.selection,  # tell pyemma the subsets of atoms
            features=features,
            topfile=input_pdb,
            tica_lag=tica_lag,
            tica_dim=tica_dim,
            msm_states=msm_states,
            msm_lag=msm_lag,
            stride=stride
        )

        return t
