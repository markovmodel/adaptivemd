def remote_analysis(
        trajectories,
        traj_name='output.dcd',
        topfile='input.pdb',
        tica_lag=2,
        tica_dim=2,
        msm_states=5,
        msm_lag=2,
        stride=1):
    """
    Remote analysis function to be called by the RPC Python call

    Parameters
    ----------
    trajectories : list of `Trajectory`
        a list of `Trajectory` objects
    traj_name : str
        name of the trajectory file with the trajectory directory given
    topfile : `File`
        a reference to the `.pdb` file using in pyemma
    tica_lag : int
        the lagtime used for tCIA
    tica_dim : int
        number of dimensions using in tICA. This refers to the number of tIC used
    msm_states : int
        number of microstates used for the MSM
    msm_lag : int
        lagtime used for the MSM construction
    stride : int
        a stride to be used on the data. Can speed up computation at reduced accuracy

    Returns
    -------
    `Model`
        a model object with a data attribute which is a dict and contains all relevant
        information about the computed MSM
    """
    import os

    import pyemma
    from adaptivemd import Model

    feat = pyemma.coordinates.featurizer(topfile)
    feat.add_backbone_torsions()

    pyemma.config.show_progress_bars = False

    print '#trajectories :', len(trajectories)

    files = [os.path.join(t, traj_name) for t in trajectories]
    inp = pyemma.coordinates.source(files, feat)

    tica_obj = pyemma.coordinates.tica(
        inp, lag=tica_lag, dim=tica_dim, kinetic_map=False)

    y = tica_obj.get_output()

    cl = pyemma.coordinates.cluster_kmeans(data=y, k=msm_states, stride=stride)
    m = pyemma.msm.estimate_markov_model(cl.dtrajs, msm_lag)

    data = {
        'input': {
            'frames': inp.n_frames_total(),
            'dimension': inp.dimension(),
            'n_trajectories': inp.number_of_trajectories(),
            'lengths': inp.trajectory_lengths(),
        },
        'tica': {
            'dimension': tica_obj.dimension(),
            'lagtime': tica_lag
        },
        'clustering': {
            'k': msm_states,
            'dtrajs': [
                t for t in cl.dtrajs
            ]
        },
        'msm': {
            'lagtime': msm_lag,
            'P': m.P,
            'C': m.count_matrix_full
        }
    }

    return Model(data)
