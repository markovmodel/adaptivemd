import argparse

from simtk.openmm.app import *
from simtk.openmm import *
import simtk.unit as u
from sys import stdout, exit
import os
import socket
import numpy as np


if __name__ == '__main__':

    # add further auto options here
    platform_properties = {
        'CUDA': ['Cuda_Device_Index', 'Cuda_Precision', 'Cuda_Use_Cpu_Pme', 'Cuda_Cuda_Compiler',
                 'Cuda_Temp_Directory', 'Cuda_Use_Blocking_Sync', 'Cuda_Deterministic_Forces'],
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
        type=int, default=100, nargs='?',
        help='store every nth interval')

    parser.add_argument(
        '--report-interval', dest='interval_report',
        type=int, default=100, nargs='?',
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

    for p in platform_properties:
        for v in platform_properties[p]:
            p_name = (p + '_' + v)
            parser.add_argument(
                '--' + p_name.lower().replace('_', '-'),
                dest=v.lower(), type=str,
                default="",
                help=('This will set the platform property `%s`. ' % p_name.replace('_', '') +
                      'If not set the environment variable '
                      '`%s` will be used instead. ' % p_name.upper()) +
                      '[NOT INSTALLED!]' if p not in platform_names else '')

    parser.add_argument(
        '-r', '--report',
        dest='report', action='store_true',
        default=False,
        help='if set then a report is send to STDOUT')

    parser.add_argument(
        '-p', '--platform', dest='platform',
        type=str, default='fastest', nargs='?',
        help=('used platform. Currently allowed choices are ' +
              ', '.join(['`%s`' % p if p in platform_names else '`(%s)`' % p for p in platform_properties.keys()]) +
              ' but are machine and installation dependend'))

    parser.add_argument(
        '--temperature',
        type=int, default=300,
        help='temperature if not given in integrator xml')

    args = parser.parse_args()

    print 'GO...'

    properties = None

    if args.platform in platform_properties:
        properties = {}
        vars = platform_properties[args.platform]
        for v in vars:
            p_name = args.platform + '_' + v
            value = os.environ.get(p_name.upper(), None)
            if hasattr(args, p_name.lower()):
                value = getattr(args, v.lower())

            if value:
                properties[
                    args.platform + '_' + v.replace('_', '')
                ] = value

    if args.platform == 'fastest':
        platform = None
    else:
        platform = Platform.getPlatformByName(args.platform)

    print 'Reading PDB'

    pdb = PDBFile(args.topology_pdb)

    print 'Done'

    with open(args.system_xml) as f:
        system_xml = f.read()
        system = XmlSerializer.deserialize(system_xml)

    with open(args.integrator_xml) as f:
        integrator_xml = f.read()
        integrator = XmlSerializer.deserialize(integrator_xml)

    print 'Initialize Simulation'

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

    print 'Done.'

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

    output_file = os.path.join(output, 'output.dcd')
    simulation.reporters.append(
        DCDReporter(output_file, args.interval_store))

    if args.report and args.verbose:
        simulation.reporters.append(
            StateDataReporter(
                stdout,
                args.interval_report,
                step=True,
                potentialEnergy=True,
                temperature=True))

    restart_file = os.path.join(output, 'restart.npz')

    print('START SIMULATION')

    simulation.step(args.length * args.interval_store)

    print('DONE')

    state = simulation.context.getState(getPositions=True, getVelocities=True)
    pbv = state.getPeriodicBoxVectors(asNumpy=True)
    vel = state.getVelocities(asNumpy=True)
    pos = state.getPositions(asNumpy=True)

    np.savez(restart_file, positions=pos, box_vectors=pbv, velocities=vel, index=args.length)

    print('Written to directory `%s`' % args.output)

    exit(0)
