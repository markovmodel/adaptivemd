from simtk.openmm.app import *
from simtk.openmm import *
from simtk.unit import *

pdb = PDBFile('alanine.pdb')

forcefield = ForceField('amber99sb.xml', 'tip3p.xml')
system = forcefield.createSystem(pdb.topology, nonbondedMethod=PME, nonbondedCutoff=1*nanometer, constraints=HBonds)
integrator = LangevinIntegrator(300*kelvin, 1/picosecond, 0.002*picoseconds)

with open('system.xml', 'w') as f:
    system_xml = XmlSerializer.serialize(system)
    f.write(system_xml)

with open('integrator.xml', 'w') as f:
    integrator_xml = XmlSerializer.serialize(integrator)
    f.write(integrator_xml)
