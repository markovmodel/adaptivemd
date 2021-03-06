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
from __future__ import absolute_import

import os

from adaptivemd import PythonTask
from adaptivemd.analysis import Analysis
from adaptivemd.mongodb import DataDict
from adaptivemd.model import Model

from ._remote import remote_analysis


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
        ``functionname: [attr1, attr2, ...]``. attributes can be results of
        function calls. All function calls are to the featurizer object!
        If a list is given each element is considered to be a feature
        descriptor. If None (default) all coordinates will be added as
        features ``.add_all()``

        Examples

        ::code

            # feat.add_backbone_torsions()
            {'add_backbone_torsions': None}

            # feat.add_distances([[0,10], [2,20]])
            {'add_distances': [ [[0,10], [2,20]] ]}

            # feat.add_inverse_distances(select_backbone())
            {'add_inverse_distances': {'select_backbone': None}}

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
    def then_func(project, task, data, inputs):
        # add the input arguments for later reference
        data['input']['trajectories'] = inputs['trajectories']
        data['input']['pdb'] = inputs['topfile']

        # from the task we get the used generator and then its outtype
        data['input']['modeller'] = task.generator

        # wrapping in a DataDict allows storage of large files!
        model = Model(DataDict(data))
        project.models.add(model)

    def execute(self,
                trajectories,
                tica_lag=10,
                tica_dim=2,
                tica_stride=2,
                msm_states=None,
                msm_lag=2,
                clust_stride=2,
                tica_weights='empirical',
                resource_name=None,
                cpu_threads=1,
                gpu_contexts=0,
                mpi_rank=0):

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
        tica_weights : str
            reweighting method for tICA calculation in pyemma.coor.tica
        msm_states : int or None
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
        t = PythonTask(self, resource_name, cpu_threads, gpu_contexts, mpi_rank)

        if resource_name is None:
            resource_name = list()
        elif isinstance(resource_name, str):
            resource_name = [resource_name]

        assert isinstance(resource_name, list)
        t.resource_name = resource_name

        # we handle the returned output ourselves -> its stored as a model
        # so do not store the returned JSON also
        t.store_output = False

        # copy the output.json to a models/model.{uuid}.json file
        t.backup_output_json(
            os.path.join('project:///models', 'model.' + hex(t.__uuid__) + '.json'))

        input_pdb = t.link(self['pdb_file_stage'], 'input.pdb')

        trajs = list(trajectories)

        if len(trajs) == 0:
            # nothing to analyze
            return

        outtype = self.outtype
        features = self.features

        for traj in trajs:
            if outtype not in traj.types:
                # oops, one of the trajectories does not have the required type!
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
            tica_stride=tica_stride,
            tica_weights=tica_weights,
            msm_states=msm_states,
            msm_lag=msm_lag,
            clust_stride=clust_stride
        )

        return t
