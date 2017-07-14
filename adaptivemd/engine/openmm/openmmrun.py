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
from __future__ import absolute_import, print_function

import os
import argparse
import ujson
from sys import stdout, exit
import socket
import numpy as np
import mdtraj as md

import simtk.unit as u
from simtk.openmm import Platform, XmlSerializer
from simtk.openmm.app import PDBFile, Simulation, DCDReporter, StateDataReporter

import time
import random



def get_xml(xml_file):
    # TODO file access control
    attempt = 0
    retries = 500
    while True:
        try:
            with open(xml_file) as f:
                xml = f.read()
                cereal = XmlSerializer.deserialize(xml)
            return xml, cereal

        except ValueError as e:
            if attempt < retries:
                attempt += 1
                time.sleep(random.random())
            else:
                raise e


def get_platform(platform_name):
    if platform_name == 'fastest':
        platform = None
    else:
        # TODO file access control
        attempt = 0
        retries = 500
        while True:
            try:
                platform = Platform.getPlatformByName(platform_name)
                return platform

            except IndexErrorError as e:
                if attempt < retries:
                    attempt += 1
                    time.sleep(random.random())
                else:
                    raise e


def get_pdbfile(topology_pdb):
    # TODO file access control
    attempt = 0
    retries = 500
    while True:
        try:
            pdb = PDBFile(topology_pdb)
            return pdb

        except IndexError as e:
            if attempt < retries:
                attempt += 1
                time.sleep(random.random())
            else:
                raise e


if __name__ == '__main__':

    print('TIMER OpenMMRun GO... {0:.5f}'.format(time.time()))

    # add further auto options here
    platform_properties = {
        'CUDA': ['Cuda_Device_Index', 'Cuda_Precision', 'Cuda_Use_Cpu_Pme',
                 'Cuda_Cuda_Compiler', 'Cuda_Temp_Directory', 'Cuda_Use_Blocking_Sync',
                 'Cuda_Deterministic_Forces'],
        'OpenCL': ['OpenCL_Device_Index', 'OpenCL_Precision', 'OpenCL_Use_Cpu_Pme',
                   'OpenCL_OpenCL_Platform_Index'],
        'CPU': ['CPU_Threads'],
        'Reference': []
    }

    platform_names = [
        Platform.getPlatform(no_platform).getName()
        for no_platform in range(Platform.getNumPlatforms())]

    parser = argparse.ArgumentParser(
        description='Run an MD simulation using OpenMM')

    parser.add_argument(
        'output',
        metavar='output/',
        help='the output directory',
        type=str)

    parser.add_argument(
        '-l', '--length', dest='length',
        type=int, default=100, nargs='?',
        help='the number of frames to be simulated')

    parser.add_argument(
        '--store-interval', dest='interval_store',
        type=int, default=1, nargs='?',
        help='store every nth interval')

    parser.add_argument(
        '--report-interval', dest='interval_report',
        type=int, default=1, nargs='?',
        help='report every nth interval')

    parser.add_argument(
        '-s', '--system', dest='system_xml',
        type=str, default='system.xml', nargs='?',
        help='the path to the system.xml file')

    parser.add_argument(
        '--restart', dest='restart',
        type=str, default='', nargs='?',
        help='the path to the restart file. If given the coordinates in the topology file '
             'will be ignored.')

    parser.add_argument(
        '-i', '--integrator', dest='integrator_xml',
        type=str, default='integrator.xml', nargs='?',
        help='the path to the integrator.xml file')

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

    parser.add_argument(
        '--types', dest='types',
        type=str, default='', nargs='?',
        help='alternative definition for output files and strides')

    for p in platform_properties:
        for v in platform_properties[p]:
            p_name = (p + '_' + v)
            parser.add_argument(
                '--' + p_name.lower().replace('_', '-'),
                dest=v.lower(), type=str,
                default="",
                help=(
                         'This will set the platform property `%s`. ' % p_name.replace('_', '') +
                         'If not set the environment variable '
                         '`%s` will be used instead. ' % p_name.upper()
                     ) + '[NOT INSTALLED!]' if p not in platform_names else ''
            )

    parser.add_argument(
        '-r', '--report',
        dest='report', action='store_true',
        default=False,
        help='if set then a report is send to STDOUT')

    parser.add_argument(
        '-p', '--platform', dest='platform',
        type=str, default='fastest', nargs='?',
        help=('used platform. Currently allowed choices are ' +
              ', '.join(['`%s`' % p if p in platform_names else '`(%s)`' % p
                         for p in platform_properties.keys()]) +
              ' but are machine and installation dependend'))

    parser.add_argument(
        '--temperature',
        type=int, default=300,
        help='temperature if not given in integrator xml')

    args = parser.parse_args()

    properties = None

    if args.platform in platform_properties:
        properties = {}
        props = platform_properties[args.platform]
        for v in props:
            p_name = args.platform + '_' + v
            value = os.environ.get(p_name.upper(), None)
            if hasattr(args, p_name.lower()):
                value = getattr(args, v.lower())

            if value:
                properties[
                    args.platform + '_' + v.replace('_', '')
                ] = value

    # Randomize order of file reading to alleviate traffic
    # from synchronization
    rand = random.random()

    print('TIMER OpenMMRun Reading PDB {0:.5f}'.format(time.time()))
    print('Done')
    print('Initialize Simulation')
    if rand < 0.041666666:
        platform = get_platform(args.platform)
        pdb = get_pdbfile(args.topology_pdb)
        system_xml, system = get_xml(args.system_xml)
        integrator_xml, integrator = get_xml(args.integrator_xml)
    elif rand < 2*0.041666666:
        platform = get_platform(args.platform)
        system_xml, system = get_xml(args.system_xml)
        pdb = get_pdbfile(args.topology_pdb)
        integrator_xml, integrator = get_xml(args.integrator_xml)
    elif rand < 3*0.041666666:
        platform = get_platform(args.platform)
        system_xml, system = get_xml(args.system_xml)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        pdb = get_pdbfile(args.topology_pdb)
    elif rand < 4*0.041666666:
        platform = get_platform(args.platform)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        pdb = get_pdbfile(args.topology_pdb)
        system_xml, system = get_xml(args.system_xml)
    elif rand < 5*0.041666666:
        platform = get_platform(args.platform)
        pdb = get_pdbfile(args.topology_pdb)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        system_xml, system = get_xml(args.system_xml)
    elif rand < 6*0.041666666:
        platform = get_platform(args.platform)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        system_xml, system = get_xml(args.system_xml)
        pdb = get_pdbfile(args.topology_pdb)
    elif rand < 7*0.041666666:
        pdb = get_pdbfile(args.topology_pdb)
        platform = get_platform(args.platform)
        system_xml, system = get_xml(args.system_xml)
        integrator_xml, integrator = get_xml(args.integrator_xml)
    elif rand < 8*0.041666666:
        pdb = get_pdbfile(args.topology_pdb)
        platform = get_platform(args.platform)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        system_xml, system = get_xml(args.system_xml)
    elif rand < 9*0.041666666:
        pdb = get_pdbfile(args.topology_pdb)
        system_xml, system = get_xml(args.system_xml)
        platform = get_platform(args.platform)
        integrator_xml, integrator = get_xml(args.integrator_xml)
    elif rand < 10*0.041666666:
        pdb = get_pdbfile(args.topology_pdb)
        system_xml, system = get_xml(args.system_xml)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        platform = get_platform(args.platform)
    elif rand < 11*0.041666666:
        pdb = get_pdbfile(args.topology_pdb)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        platform = get_platform(args.platform)
        system_xml, system = get_xml(args.system_xml)
    elif rand < 12*0.041666666:
        pdb = get_pdbfile(args.topology_pdb)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        system_xml, system = get_xml(args.system_xml)
        platform = get_platform(args.platform)
    elif rand < 13*0.041666666:
        integrator_xml, integrator = get_xml(args.integrator_xml)
        pdb = get_pdbfile(args.topology_pdb)
        platform = get_platform(args.platform)
        system_xml, system = get_xml(args.system_xml)
    elif rand < 14*0.041666666:
        integrator_xml, integrator = get_xml(args.integrator_xml)
        system_xml, system = get_xml(args.system_xml)
        pdb = get_pdbfile(args.topology_pdb)
        platform = get_platform(args.platform)
    elif rand < 15*0.041666666:
        integrator_xml, integrator = get_xml(args.integrator_xml)
        pdb = get_pdbfile(args.topology_pdb)
        system_xml, system = get_xml(args.system_xml)
        platform = get_platform(args.platform)
    elif rand < 16*0.041666666:
        integrator_xml, integrator = get_xml(args.integrator_xml)
        platform = get_platform(args.platform)
        pdb = get_pdbfile(args.topology_pdb)
        system_xml, system = get_xml(args.system_xml)
    elif rand < 17*0.041666666:
        integrator_xml, integrator = get_xml(args.integrator_xml)
        system_xml, system = get_xml(args.system_xml)
        platform = get_platform(args.platform)
        pdb = get_pdbfile(args.topology_pdb)
    elif rand < 18*0.041666666:
        integrator_xml, integrator = get_xml(args.integrator_xml)
        platform = get_platform(args.platform)
        system_xml, system = get_xml(args.system_xml)
        pdb = get_pdbfile(args.topology_pdb)
    elif rand < 19*0.041666666:
        system_xml, system = get_xml(args.system_xml)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        pdb = get_pdbfile(args.topology_pdb)
        platform = get_platform(args.platform)
    elif rand < 20*0.041666666:
        system_xml, system = get_xml(args.system_xml)
        pdb = get_pdbfile(args.topology_pdb)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        platform = get_platform(args.platform)
    elif rand < 21*0.041666666:
        system_xml, system = get_xml(args.system_xml)
        platform = get_platform(args.platform)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        pdb = get_pdbfile(args.topology_pdb)
    elif rand < 22*0.041666666:
        system_xml, system = get_xml(args.system_xml)
        integrator_xml, integrator = get_xml(args.integrator_xml)
        platform = get_platform(args.platform)
        pdb = get_pdbfile(args.topology_pdb)
    elif rand < 23*0.041666666:
        system_xml, system = get_xml(args.system_xml)
        platform = get_platform(args.platform)
        pdb = get_pdbfile(args.topology_pdb)
        integrator_xml, integrator = get_xml(args.integrator_xml)
    else:
        system_xml, system = get_xml(args.system_xml)
        pdb = get_pdbfile(args.topology_pdb)
        platform = get_platform(args.platform)
        integrator_xml, integrator = get_xml(args.integrator_xml)

    try:
        simulation = Simulation(
            pdb.topology,
            system,
            integrator,
            platform,
            properties
        )
    except Exception:
        print('EXCEPTION', (socket.gethostname()))
        raise

    print('Done.')

    print('# platform used:', simulation.context.getPlatform().getName())

    if args.verbose:
        print('# platforms available')
        for no_platform in range(Platform.getNumPlatforms()):
            # noinspection PyCallByClass,PyTypeChecker
            print('(%d) %s' % (no_platform, Platform.getPlatform(no_platform).getName()))

        print(os.environ)

        print(Platform.getPluginLoadFailures())
        print(Platform.getDefaultPluginsDirectory())

    if args.restart:
        arr = np.load(args.restart)
        simulation.context.setPositions(arr['positions'] * u.nanometers)
        simulation.context.setVelocities(arr['velocities'] * u.nanometers/u.picosecond)
        simulation.context.setPeriodicBoxVectors(*arr['box_vectors'] * u.nanometers)
    else:
        simulation.context.setPositions(pdb.positions)
        pbv = pdb.getTopology().getPeriodicBoxVectors()
        simulation.context.setPeriodicBoxVectors(*pbv)
        # set velocities to temperature in integrator
        try:
            temperature = integrator.getTemperature()
        except AttributeError:
            assert args.temperature > 0
            temperature = args.temperature * u.kelvin

        print('# temperature:', temperature)

        simulation.context.setVelocitiesToTemperature(temperature)

    output = args.output

    if args.types:
        # seems like we have JSON
        types_str = args.types.replace("'", '"')
        print(types_str)
        types = ujson.loads(types_str)
        if isinstance(types, dict):
            for name, opts in types.items():
                if 'filename' in opts and 'stride' in opts:
                    output_file = os.path.join(output, opts['filename'])

                    selection = opts['selection']
                    if selection is not None:
                        mdtraj_topology = md.Topology.from_openmm(pdb.topology)
                        atom_subset = mdtraj_topology.select(selection)
                    else:
                        atom_subset = None

                    simulation.reporters.append(
                        md.reporters.DCDReporter(
                            output_file, opts['stride'], atomSubset=atom_subset))

                    print('Writing stride %d to file `%s` with selection `%s`' % (
                        opts['stride'], opts['filename'], opts['selection']))

    else:
        # use defaults from arguments
        output_file = os.path.join(output, 'output.dcd')
        simulation.reporters.append(
            DCDReporter(output_file, args.interval_store))

    if not args.restart:
        # if not a restart write first frame
        state = simulation.context.getState(getPositions=True)
        for r in simulation.reporters:
            r.report(simulation, state)

    if args.report and args.verbose:
        simulation.reporters.append(
            StateDataReporter(
                stdout,
                args.interval_report,
                step=True,
                potentialEnergy=True,
                temperature=True))

    restart_file = os.path.join(output, 'restart.npz')

    print('TIMER OpenMMRun START SIMULATION {0:.5f}'.format(time.time()))

    simulation.step(args.length)

    print('TIMER OpenMMRun END SIMULATION {0:.5f}'.format(time.time()))

    state = simulation.context.getState(getPositions=True, getVelocities=True)
    pbv = state.getPeriodicBoxVectors(asNumpy=True)
    vel = state.getVelocities(asNumpy=True)
    pos = state.getPositions(asNumpy=True)

    np.savez(restart_file, positions=pos, box_vectors=pbv, velocities=vel, index=args.length)

    print('Written to directory `%s`' % args.output)

    print('TIMER OpenMMRun DONE {0:.5f}'.format(time.time()))

    exit(0)
