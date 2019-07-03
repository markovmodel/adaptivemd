
from simtk.openmm.app import *
from simtk.openmm import *
from simtk.unit import *

#pdb    = PDBFile('alanine.pdb')
#ff     = ForceField('amber99sb.xml')

pdb    = PDBFile('alanine_autopsf.pdb')
psf    = CharmmPsfFile('alanine_autopsf.psf')
ff     = ForceField('charmm36.xml')

psf.setBox(*(3*[1.2*nanometers]))

model = Modeller(
    psf.topology,
    pdb.positions,
)

system = ff.createSystem(
    model.topology,
    nonbondedMethod=PME,
    nonbondedCutoff=1*nanometer,
    constraints=AllBonds,
    hydrogenMass=4*amu,
)

integrator = LangevinIntegrator(
    300*kelvin,
    1/picosecond,
    0.005*picoseconds,
)

with open('system.xml', 'w') as f:
    system_xml = XmlSerializer.serialize(system)
    f.write(system_xml)

with open('integrator.xml', 'w') as f:
    integrator_xml = XmlSerializer.serialize(integrator)
    f.write(integrator_xml)
