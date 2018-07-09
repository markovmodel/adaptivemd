##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: Jan-Hendrik Prinz
# Contributors:
#
# `adaptiveMD` is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with MDTraj. If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from __future__ import print_function

# The remote function to be called py PyEMMAAnalysis


#  #TODO --> upgrade remote_analysis structure to accommodate
#            model / analysis variations ...
#            should take set of pars and func name args
#            --> pull func: have required pars, optional pars
#                --> pull pars from args pool
def remote_analysis(
        trajectories,
        traj_name='output.dcd',
        selection=None,
        features=None,
        topfile='input.pdb',
        tica_lag=2,
        tica_dim=2,
        tica_stride=2,
        msm_states=5,
        msm_lag=2,
        clust_stride=2):
    """
    Remote analysis function to be called by the RPC Python call

    Parameters
    ----------
    trajectories : Sized of `Trajectory`
        a list of `Trajectory` objects
    traj_name : str
        name of the trajectory file with the trajectory directory given
    selection : str
        an atom subset selection string as used in mdtraj .select
    features : dict, list<dict>, or None
        A feature descriptor, or list thereof. Each features dict is
        used to add exactly one feature to PyEMMA's MDFeaturizer.
        The features dict may contain only 1 or 2 entries. One entry
        must be the name of an MDFeaturizer method 'add_xxx'. The
        contents are either None (implied in 1.), or a list/tuple
        of explicit positional arguments for 'methodname'.

        1. {methodname: [attr1, attr2, ...]}
        2. {methodname: {attr1: <contents>}}
        3. {methodname: [{attr1: <contents>}, {attr2: <contents>}]}
        4. [{method1: <contents>}, {method2: <contents>}]


        The attributes are results of method calls on the MDFeaturizer,
        such as 'select_Backbone' to provide arguments for the 'methodname'
        call. All function calls are to the featurizer object! The
        dicts storing 'attrN' follow the same design as the outer method,
        since these dicts are used identically to call methods of
        the MDFeaturizer object.
        If a list is given as in 4., each element is considered to be
        a feature descriptor. If None (default) all coordinates will be
        added as features (.add_all())
        The optional second entry in a features dict is used to specify
        keyword arguments to the methods. The key for this entry must
        be 'kwargs', and its value must be a dict of key-value pairs
        corresponding to argument names, and the values to pass. Again,
        this format is used for calling MDFeaturizer methods and so
        can be used at either level of the features dict.

        5. {methodname: {attr1: [ positionals ],
                         kwargs: {kwarg1: value1}},
            kwargs: {kwarg1: value1, kwarg2: value2}}


    topfile : `File`
        a reference to the full topology `.pdb` file using in pyemma
    tica_lag : int
        the lagtime used for tICA
    tica_dim : int
        number of dimensions using in tICA. This refers to the number of tIC used
    tica_stride : int
        a stride to be used in tICA calculation. Can speed up computation at reduced accuracy
    msm_states : int
        number of microstates used for the MSM
    msm_lag : int
        lagtime used for the MSM construction
    clust_stride : int
        a stride to be used on when determining cluster centers. Can speed up computation at reduced accuracy

    Returns
    -------
    `Model`
        a model object with a data attribute which is a dict and contains all relevant
        information about the computed MSM

    Examples
    --------

    The features_dict has multiple structures to create different call signatures
    on the PyEMMA MD Featurizer. Here are some examples showing a dict vs call.

        {'add_backbone_torsions': None}
        -> feat.add_backbone_torsions()

        {'add_distances': [ [[0,10], [2,20]] ]}
        -> feat.add_distances([[0,10], [2,20]])

        {'add_inverse_distances': [
            { 'select_backbone': None } ]}
        -> feat.add_inverse_distances(select_backbone())

        {'add_residue_mindist': None,
         'kwargs': {'threshold': 0.6, 'scheme': 'ca'}}
        -> feat.add_residue_mindist(threshold=0.6, scheme='ca')

        {'add_distances': [ [1,2,3,4] ],
         'kwargs': {'indices2': [10,11,12,13]}}
        -> feat.add_distances([1,2,3,4], indices2=[10,11,12,13])

     These two are equivalent:

        {'add_distances': {'select': None,
                           'kwargs': {'selstring':
                                      'resname GLN and (mass 11 to 17)'}},
         'kwargs': {'indices2': [10,11,12,13]}}

        {'add_distances': {'select': [ 'resname GLN and (mass 11 to 17)' ] },
         'kwargs': {'indices2': [10,11,12,13]}}

        -> feat.add_distances(select('resname GLN and (mass 11 to 17)'),
                              indices2=[10,11,12,13])

     Ionic Contacts (Salt Bridges):

        pos = 'rescode K or rescode R or rescode H'
        neg = 'rescode D or rescode E'
        {'add_distances': {'select': [ pos ]},
         'kwargs': {'indices2': {'select': [ neg ] }}}


    """
    import os

    import pyemma
    import mdtraj as md

    pdb = md.load(topfile)
    topology = pdb.topology

    # Number of MSM Eigendimensions to save
    d = 10

    if selection:
        topology = topology.subset(topology.select(selection_string=selection))

    feat = pyemma.coordinates.featurizer(topology)

    if features:
        # TODO  this function needs tests
        #       - it is super important to make the arguments
        #         available to the pyemma methods
        def apply_feat_part(featurizer, parts):
            if isinstance(parts, dict):

                items = list(parts.items())
                if len(items) == 1:
                    func, attributes = items[0]
                    kwargs = dict()

                elif len(items) == 2:
                    if items[0][0] == 'kwargs':
                        func, attributes = items[1]
                        key, kwargs = items[0]

                    elif items[1][0] == 'kwargs':
                        func, attributes = items[0]
                        key, kwargs = items[1]

                    for k,v in kwargs.items():
                        if isinstance(v, dict):

                            _func, _attr = list(v.items())[0]
                            _f = getattr(featurizer, _func)
                            if _attr is None:
                                idc = _f()

                            elif isinstance(_attr, (list, tuple)):
                                idc = _f(*apply_feat_part(featurizer,
                                         _attr))

                            kwargs[k] = idc

                assert isinstance(kwargs, dict)
                f = getattr(featurizer, func)

                if attributes is None:
                    return f(**kwargs)

                elif isinstance(attributes, (list, tuple)):
                    return f(*apply_feat_part(featurizer, attributes),
                             **kwargs)
                else:
                    return f(apply_feat_part(featurizer, attributes),
                             **kwargs)
        
            elif isinstance(parts, (list, tuple)):
                return [apply_feat_part(feat, q)
                        for q in parts]
            else:
                return parts

        apply_feat_part(feat, features)

    else:
        feat.add_all()

    pyemma.config.show_progress_bars = False

    print('#trajectories :', len(trajectories))

    files = [os.path.join(t, traj_name) for t in trajectories]
    inp = pyemma.coordinates.source(files, feat)

    tica_obj = pyemma.coordinates.tica(inp, lag=tica_lag,
                   dim=tica_dim, kinetic_map=True, stride=tica_stride)

    y = tica_obj.get_output()

    cl = pyemma.coordinates.cluster_kmeans(data=y, k=msm_states,
             max_iter=50, stride=clust_stride)

    m = pyemma.msm.estimate_markov_model(cl.dtrajs, msm_lag)

    data = {
        'input': {
            'n_atoms': topology.n_atoms,
            'frames': inp.n_frames_total(),
            'n_trajectories': inp.number_of_trajectories(),
            'lengths': inp.trajectory_lengths(),
            'selection': selection
        },
        'features': {
            'features': features,
            'n_features': inp.dimension(),
        },
        'tica': {
            'dimension':    tica_obj.dimension(),
            'lagtime':      tica_lag,
            'eigenvalues':  tica_obj.eigenvalues,
            'eigenvectors': tica_obj.eigenvectors,
        },
        'clustering': {
            'k':       msm_states,
            'dtrajs':  [ t for t in cl.dtrajs ],
            'centers': cl.clustercenters,
        },
        'msm': {
            'lagtime': msm_lag,
            'P': m.P,
            'C': m.count_matrix_full,
            'eigenvalues': m.eigenvalues(d),
            'l_eigenvectors': m.eigenvectors_left(d),
            'r_eigenvectors': m.eigenvectors_right(d),
        }
    }

    return data
