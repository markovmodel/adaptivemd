from adaptivemd import Model


def remote_analysis(
        files,
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
    files : list of `Trajectory`
        a list of `Trajectory` objects
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
    import pyemma

    feat = pyemma.coordinates.featurizer(topfile)
    feat.add_backbone_torsions()

    pyemma.config.show_progress_bars = False

    # todo: allow specification of several folders and wildcats, used for session handling
    # if isinstance(trajfiles, basestring):
    #     if '*' in trajfiles or trajfiles.endswith('/'):
    #         files = glob.glob(trajfiles)

    print '#files :', len(files)

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
