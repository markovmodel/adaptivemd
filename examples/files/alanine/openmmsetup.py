
from simtk.openmm.app import *
from simtk.openmm import *
from simtk.unit import *

#pdb    = PDBFile('alanine.pdb')
#ff     = ForceField('amber99sb.xml')

pdb    = PDBFile('alanine_autopsf.pdb')
psf    = CharmmPsfFile('alanine_autopsf.psf')
ff     = ForceField('charmm36.xml', 'charmm36/water.xml')

psf.setBox(*(3*[2.*nanometers]))

model = Modeller(
    psf.topology,
    pdb.positions,
)

#model.addHydrogens(ff)
model.deleteWater()
model.addSolvent(ff)

system = ff.createSystem(
    model.topology,
    nonbondedMethod=PME,
    nonbondedCutoff=0.95*nanometer,
    constraints=AllBonds,
    hydrogenMass=4*amu,
)

integrator = LangevinIntegrator(
    300*kelvin,
    1/picosecond,
    0.005*picoseconds,
)

PDBFile.writeFile(model.topology, model.positions, open('alanine.pdb', 'w'))

with open('system.xml', 'w') as f:
    system_xml = XmlSerializer.serialize(system)
    f.write(system_xml)

with open('integrator.xml', 'w') as f:
    integrator_xml = XmlSerializer.serialize(integrator)
    f.write(integrator_xml)
