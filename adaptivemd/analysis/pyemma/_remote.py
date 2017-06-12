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


def remote_analysis(
        trajectories,
        traj_name='output.dcd',
        selection=None,
        features=None,
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
    trajectories : Sized of `Trajectory`
        a list of `Trajectory` objects
    traj_name : str
        name of the trajectory file with the trajectory directory given
    selection : str
        an atom subset selection string as used in mdtraj .select
    features : dict or list or None
        a feature descriptor in the format. A dict has exactly one entry:
        functionname: [attr1, attr2, ...]. attributes can be results of
        function calls. All function calls are to the featurizer object!
        If a list is given each element is considered to be a feature
        descriptor. If None (default) all coordinates will be added as
        features (.add_all())

        Examples

            {'add_backbone_torsions': None}
            -> feat.add_backbone_torsions()

            {'add_distances': [ [[0,10], [2,20]] ]}
            -> feat.add_distances([[0,10], [2,20]])

            {'add_inverse_distances': [
                { 'select_backbone': None } ]}
            -> feat.add_inverse_distances(select_backbone())

    topfile : `File`
        a reference to the full topology `.pdb` file using in pyemma
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
    import mdtraj as md

    pdb = md.load(topfile)
    topology = pdb.topology

    if selection:
        topology = topology.subset(topology.select(selection_string=selection))

    feat = pyemma.coordinates.featurizer(topology)

    if features:
        def apply_feat_part(featurizer, parts):
            if isinstance(parts, dict):
                func, attributes = list(parts.items())[0]
                f = getattr(featurizer, func)
                if attributes is None:
                    return f()
                if isinstance(attributes, (list, tuple)):
                    return f(*apply_feat_part(featurizer, attributes))
                else:
                    return f(apply_feat_part(featurizer, attributes))
            elif isinstance(parts, (list, tuple)):
                return [apply_feat_part(featurizer, q) for q in parts]
            else:
                return parts

        apply_feat_part(feat, features)
    else:
        feat.add_all()

    pyemma.config.show_progress_bars = False

    print('#trajectories :', len(trajectories))

    files = [os.path.join(t, traj_name) for t in trajectories]
    inp = pyemma.coordinates.source(files, feat)

    tica_obj = pyemma.coordinates.tica(
        inp, lag=tica_lag, dim=tica_dim, kinetic_map=False)

    y = tica_obj.get_output()

    cl = pyemma.coordinates.cluster_kmeans(data=y, k=msm_states, stride=stride)
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

    return data
