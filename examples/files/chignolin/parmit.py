#!/usr/bin/env python


import sys
from setupsystem import SystemSetup


if __name__ == "__main__":

    # Forcefield
    ff_type = "charmm"
    topfile = "top_all22star_prot.inp"
    parfile = "par_all22star_prot_R1.inp"

    # Coordinates and Topology
    pdbfile = "chignolin.pdb"
    psffile = "chignolin.psf"

    # Simulation
    integrator ="LangevinIntegrator"
    timestep    = 5   #* unit.femtosecond
    cutoff      = 9.5 #* unit.nanometer
    temperature = 340 #* unit.kelvin

    # Flat folder structure, not used
    files_folder = ""
    output_folder = ""

    files_input = dict()
    files_input['coords']  = pdbfile
    files_input['psf']     = psffile
    files_input['topo']    = topfile
    files_input['pars']    = parfile
    files_input['ff_type'] = ff_type

    ss = SystemSetup(
        stepSize=timestep,
        nonbondedCutoff=cutoff,
        temperature=temperature
    )

    ss.set_systemfiles(**files_input)

    ss.read_files()
    ss.set_all_args()
    ss.create_system()
    ss.create_integrator(integrator)

    ss.write_xmls(folder=output_folder)

