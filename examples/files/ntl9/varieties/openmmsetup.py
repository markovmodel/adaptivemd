#!/usr/bin/env/python

'''
    Simple resetup of ntl9 files for different cutoffs and timesteps.
    Maybe will expand to include different options and/or systems.

    Usage:
    ------
    $ python openmmsetup.py setup_name  cutoff  long_timestep

    [positional]
    setup_name : `string`
        used as folder name for new system files

    [optional]

    cutoff : `float`
        to specify the Coloumb calculation cutoff

    long_timestep : "-longts"
        flag to specify a long timestep used in integration.
        Hydrogen and heavy atom masses will be repartitioned

'''

from __future__ import print_function
import sys, os

import simtk.openmm.app as app
import simtk.openmm as mm
import simtk.unit as u
from parmed import gromacs

#### do like this:
###class OpenMMSetup(object):
###    # details of setup
###
###if argname in class.__dict__:
###    class.__dict__[argname] = argval


def mk_new_setup(newdir, pme_cutoff=1, massrepart=False):

    pme_cutoff = float(pme_cutoff)

    system_kwargs = dict(
        nonbondedMethod=app.PME,
        nonbondedCutoff=pme_cutoff * u.nanometer)

    # user parameters
    if massrepart:
        integrator_timestep = 0.005  # picoseconds
        system_kwargs.update(dict(constraints  = app.AllBonds))
        system_kwargs.update(dict(hydrogenMass = 4*u.amu))

    else:
        integrator_timestep = 0.002  # picoseconds
        system_kwargs.update(dict(constraints  = app.HBonds))

   #del# save_traj_ps = 10  # picoseconds
   #del# save_full_traj_ps = 100  # picoseconds
   #del# save_restart_file_ns = 100 # nanoseconds

    # physical values:
    temperature = 300 * u.kelvin
    pressure = 1 * u.bar
    friction = 1

    # load pdb, force field and create system
    gromacs.GROMACS_TOPDIR = 'toppar'

    top = gromacs.GromacsTopologyFile('toppar/topol-NTL9.top')
    gro = gromacs.GromacsGroFile.parse('toppar/start-NTL9.gro')
    top.box = gro.box

    # system
    [print('{0}:'.format(k), v) for k,v in system_kwargs.items()]
    system = top.createSystem(**system_kwargs)

    # integrator
    integrator = mm.LangevinIntegrator(
        temperature * u.kelvin,
        friction / u.picosecond,
        integrator_timestep * u.picoseconds)

    os.mkdir(newdir)

    gro.write_pdb('{0}/ntl9.pdb'.format(newdir))

    with open('{0}/system.xml'.format(newdir), 'w') as f:
        system_xml = mm.XmlSerializer.serialize(system)
        f.write(system_xml)

    with open('{0}/integrator.xml'.format(newdir), 'w') as f:
        integrator_xml = mm.XmlSerializer.serialize(integrator)
        f.write(integrator_xml)


if __name__ == '__main__':

    newvarname=sys.argv[1]

    cutoff = 1
    if len(sys.argv) > 2:
        cutoff = sys.argv[2]

    increase_timestep = False
    if len(sys.argv) == 4:
        if sys.argv[3] == '-longts':
            increase_timestep = True

    mk_new_setup(newvarname,
                 pme_cutoff=cutoff,
                 massrepart=increase_timestep)

