import pyemma.coordinates as coor
import pyemma.msm as msm

import numpy as np
import argparse
from sys import exit
from pyemma import config

import json

import logging

logging.disable(logging.CRITICAL)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze a number of files and compute an MSM')

    parser.add_argument(
        'file',
        metavar='input.dcd',
        help='the output .dcd file',
        type=str, nargs='+')

    parser.add_argument(
        '-c', '--tica-lagtime', dest='tica_lag',
        type=int, default=2, nargs='?',
        help='the lagtime used for tica')

    parser.add_argument(
        '-d', '--tica-dimensions', dest='tica_dim',
        type=int, default=2, nargs='?',
        help='the lagtime used for tica')

    parser.add_argument(
        '-s', '--stride', dest='stride',
        type=int, default=1, nargs='?',
        help='the lagtime used for tica')

    parser.add_argument(
        '-l', '--msm-lagtime', dest='msm_lag',
        type=int, default=2, nargs='?',
        help='the lagtime used for the final msm')

    parser.add_argument(
        '-k', '--msm-states', dest='msm_states',
        type=int, default=5, nargs='?',
        help='number of k means centers and number of msm states')

    parser.add_argument(
        '-t', '--topology', dest='topology_pdb',
        type=str, default='topology.pdb', nargs='?',
        help='the path to the topology.pdb file')

    parser.add_argument(
        '-v', '--verbose',
        dest='verbose', action='store_true',
        default=False,
        help='if set then text output is send to the ' +
             'console.')

    args = parser.parse_args()

    # Load files / replace by linked files

    trajfiles = args.file
    topfile = args.topology_pdb

    print trajfiles

    # Choose parameters to be used in the task

    config.show_progress_bars = False

    lag = args.tica_lag

    feat = coor.featurizer(topfile)
    feat.add_backbone_torsions()

    # print feat.describe()

    inp = coor.source(trajfiles, feat)
    # print 'trajectory length = ', inp.trajectory_length(0)
    # print 'number of dimension = ', inp.dimension()

    dim = args.tica_dim

    tica_obj = coor.tica(inp, lag=lag, dim=dim, kinetic_map=False)
    Y = tica_obj.get_output()

    # print 'Mean values: ', np.mean(Y, axis=0)
    # print 'Variances:   ', np.var(Y, axis=0)

    # print -lag / np.log(tica_obj.eigenvalues[:dim])

    # clr = coor.cluster_regspace(data=Y, dmin=0.5)
    cl = coor.cluster_kmeans(data=Y, k=args.msm_states, stride=args.stride)

    M = msm.estimate_markov_model(cl.dtrajs, args.msm_lag)

    # print 'fraction of states used = ', M.active_state_fraction
    # print 'fraction of counts used = ', M.active_count_fraction

    # print M.timescales()

    # print cl.dtrajs

    # os.makedirs('dtrajs/')

    with open("model.dtraj", "w") as f:
        f.write("\n".join(" ".join(map(str, x)) for x in cl.dtrajs))

    # np.savetxt("model.dtraj", cl.dtrajs, delimiter=" ", fmt='%d')
    np.savetxt("model.msm", M.P, delimiter=",")

    # print M.P

    data = {
        'input': {
            'frames': inp.n_frames_total(),
            'dimension': inp.dimension(),
            'trajectories': inp.number_of_trajectories(),
            'lengths': inp.trajectory_lengths().tolist(),
        },
        'tica': {
            'dimension': tica_obj.dimension()
        },
        'clustering': {
            'dtrajs': [
                t.tolist() for t in cl.dtrajs
            ]
        },
        'msm': {
            'P': M.P.tolist()
        }
    }

    print json.dumps(data)

    exit(0)
