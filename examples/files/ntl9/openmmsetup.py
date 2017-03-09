import simtk.openmm.app as app
import simtk.openmm as mm
import simtk.unit as u
from parmed import gromacs

# user parameters
integrator_timestep_ps = 0.005  # picoseconds
save_traj_ps = 10  # picoseconds
save_full_traj_ps = 100  # picoseconds
save_restart_file_ns = 100 # nanoseconds

# physical values:
temperature = 300 * u.kelvin
pressure = 1 * u.bar

# load pdb, force field and create system
gromacs.GROMACS_TOPDIR = 'top'


top = gromacs.GromacsTopologyFile('files/topol-NTL9.top')
gro = gromacs.GromacsGroFile.parse('files/start-NTL9.gro')
top.box = gro.box

# system
system = top.createSystem(
    nonbondedMethod=app.PME,
    nonbondedCutoff=1 * u.nanometer,
    constraints=app.HBonds)

# integrator
integrator = mm.LangevinIntegrator(
    300 * u.kelvin,
    1 / u.picosecond,
    0.002 * u.picoseconds)

gro.write_pdb('files/input.pdb')

with open('files/system.xml', 'w') as f:
    system_xml = mm.XmlSerializer.serialize(system)
    f.write(system_xml)

with open('files/integrator.xml', 'w') as f:
    integrator_xml = mm.XmlSerializer.serialize(integrator)
    f.write(integrator_xml)
