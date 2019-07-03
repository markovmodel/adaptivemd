'''
This file contains helper objects to organize
the usage of parmed for preparation of system
files for simulation in OpenMM.
'''


from __future__ import print_function

import sys
sys.dont_write_bytecode = True

import os

import parmed
import simtk.openmm.app as app
import simtk.openmm as mm
import simtk.unit as u


class SystemFiles(object):
    '''
    This class organizes the files that
    will be used to define the system
    and the parameters for its simulation.

    The system itelf is currently rigid,
    once set it cannot be changed.

    The forcefield can be changed after
    it is set to parameterize the same
    system with different forces.

    '''
    _pdb_extension = '.pdb'
    _psf_extension = '.psf'
    _gro_extension = '.gro'
    # same extension, different idea in different cases
    _top_extension = '.top'


    def __init__(self, folder="", coords="", psf="", pars="", topo="", ff_folder="", waterbox=None):

        super(SystemFiles, self).__init__()

        # TODO FIXME get the python session directory and assume
        #            we're dealing with all relative paths
        self._files_prefix   = os.path.realpath(os.getcwd())
        #self._files_prefix   = '$HOME/ff_work/'

        self._files_folder = folder
        self._ff_folder    = ff_folder
        # NOTE sometimes only parfile is needed
        #       - topfile is is for CHARMM-like
        #         where 2 files specify the ff
        self._par          = pars
        self._top          = topo
        self._coords       = coords
        self._psf          = psf

        if self._coords.endswith(SystemFiles._pdb_extension):
            self._pdb_file = os.path.join(self._files_prefix, self._files_folder, self._coords)

        if self._psf.endswith(SystemFiles._psf_extension):
            self._psf_file = os.path.join(self._files_prefix, self._files_folder, self._psf)

    @property
    def sys_folder(self):
        return os.path.expandvars(os.path.join(
                self._files_prefix,
                self._files_folder
        ))

    @sys_folder.setter
    def sys_folder(self, sys_folder):
        if self._files_folder == None:
            self._files_folder = sys_folder
        else:
            print("System Folder already initialized")

    @property
    def pdbfile(self):
        return self._pdb_file

    @property
    def psffile(self):
        return self._psf_file

    @property
    def ff_folder(self):
        return os.path.expandvars(os.path.join(
                self._files_prefix,
                self._ff_folder
        ))

    @property
    def topfile(self):
        return os.path.join(self.ff_folder, self._top)

    @property
    def parfile(self):
        return os.path.join(self.ff_folder, self._par)


class SystemSetup(object):

    _xmls = {
        'system':     'system.xml',
        'integrator': 'integrator.xml'
    }

    _units = {
        'temperature':     u.kelvin,
        'frictionCoeff':   1/u.picosecond,
        'hydrogenMass':    u.amu,
        'nonbondedCutoff': u.angstrom,
        'stepSize':        u.femtosecond,
        'pressure':        u.bar,
    }

    #_integrator_kwargs = {
    _integrator_args = [
       'temperature',
       'frictionCoeff',
       'stepSize',
       #'pressure',
    ]

    _system_kwargs = {
        'nonbondedMethod',
        'nonbondedCutoff',
        # These ones out since its changed
        # via the stepSize attribute, so it
        # shouldn't show up in the generic
        # scrolling of set_systemkwargs
        #'constraints',
        #'hydrogenMass',
    }

    def __init__(self, **kwargs):
        super(SystemSetup, self).__init__()

        self.system_kwargs = dict()
        #self.integrator_kwargs = dict()
        self.integrator_args = list()

        self.boundary        = None
        self.temperature     = 300
        self.pressure        = 1
        self.stepSize        = 2
        self.frictionCoeff   = 1
        self.nonbondedCutoff = 12
        self.nonbondedMethod = app.PME
        self.solvent         = False
        #TODO conform delete of this attribute#self._modeller       = None

        for k,v in kwargs.items():
            if hasattr(self, k):
                print("Resetting attribute {k}: value {v} ".format(k=k,v=v))
                setattr(self, k, v)
            else:
                # TODO
                # Make this into a warning
                print("The `systemsetup` class has no attribute '{0}'".format(k))

    def set_systemfiles(self, *args, **kwargs):
        self.ff_type     = kwargs.pop('ff_type', None)
        self.systemfiles = SystemFiles(*args, **kwargs)

    def read_files(self, ff_type=None):
        if not ff_type:
            if self.ff_type:
                ff_type = self.ff_type
            else:
                print("No forcefield type has been provided, cannot read files")


        if ff_type == 'gromacs':
            parmed.gromacs.GROMACS_TOPDIR = self._files_folder
            self.params   = None
            self.coords   = parmed.gromacs.GromacsGroFile(self._coords)
            self.topo     = parmed.gromacs.GromacsTopologyFile(self._top)

        elif ff_type == 'charmm':
            self.params = parmed.charmm.CharmmParameterSet(
                self.systemfiles.parfile,
                self.systemfiles.topfile
            )

            self.topo = parmed.charmm.CharmmPsfFile(
                self.systemfiles.psffile
            )

            self.coords = app.PDBFile(
                self.systemfiles.pdbfile
            )

        else:
            print("Unsupported forcefield type: {}".format(ff_type))

      ##  if not os.path.exists(self.systemfiles.psffile):
      ##      # TODO this writes atom names and not types
      ##      #      which are usually in next column in PSF
      ##      #      ie doesn't work, fix or delete
      ##      structure = parmed.load_file(self.systemfiles.pdbfile)
      ##      structure.write_psf(self.systemfiles.psffile)

        # no need to reset since only ff can change
        print("SOLVAING? {}".format(self.solvent))
        if self.solvent:
            self.solvate()

        if self.boundary is None:
            self.setup_box()

    def solvate(self):
        print("Solvating with these parameters to Modeller.addSolvent:\n{}".format(self.solvent))
        #forcefield = app.ForceField('charmm36.xml')
        #modeller = app.Modeller(self.coords.topology, self.coords.positions)
        modeller = app.Modeller(self.coords.topology, self.coords.positions, self.topo)
        #modeller.addHydrogens(self.params)
        modeller.addSolvent(self.params, **self.solvent)
        self.structure = parmed.openmm.load_topology(modeller.topology, xyz=modeller.positions)
      #  self.structure.save('fullsystem.psf')
        self.structure.save('fullsystem.pdb')
      #  self.topo = app.CharmmPsfFile('fullsystem.psf')
      #  self.coords = app.PDBFile('fullsystem.pdb')
        self._modeller = modeller

    def create_system(self):
        if self.ff_type == "charmm":
            system_kwargs = dict(**self.system_kwargs)
            system_kwargs['params'] = self.params

        print("Using the given PDB/PSF Topologies to create system")
        self.system = self.topo.createSystem(**system_kwargs)
        print("N Constraints:", self.system.getNumConstraints())

    def set_systemkwargs(self, **kwargs):

        # Not all system kwargs have unit
        for sk in self.__class__._system_kwargs:
            try:
                unit  = self.__class__._units[sk]
                value = getattr(self, sk) * unit

            except KeyError:
                value = getattr(self, sk)

            self.system_kwargs.update({sk: value})

        if self.stepSize >= 3:# * u.femtosecond:
            self.system_kwargs.update(
                    {'constraints': app.AllBonds}
            )
            self.system_kwargs.update(
                    {'hydrogenMass': 4}
            )

        else:
            self.system_kwargs.update(
                    {'constraints':
                        #None},
                        app.HBonds},
            )

    def set_integratorargs(self):
        for ik in self.__class__._integrator_args:
            unit = self.__class__._units[ik]
            try:
                self.integrator_args.append(
                    getattr(self, ik)*unit
                )
            except AttributeError as e:
                print("Messed up:")
                print(e)
                pass

        print("Integrator Args after processing: ", self.integrator_args)

    def set_all_args(self):
        self.set_integratorargs()
        #self.set_integratorkwargs()
        self.set_systemkwargs()

    def setup_box(self):
        self.boundary = self.get_sys_boundary()
        #as vectors#boxvecs = [
        #as vectors#    [self.boundary[1][0] - self.boundary[0][0],
        #as vectors#     u.Quantity(0.0, u.nanometer),
        #as vectors#     u.Quantity(0.0, u.nanometer)
        #as vectors#    ],
        #as vectors#    [u.Quantity(0.0, u.nanometer),
        #as vectors#     self.boundary[1][1] - self.boundary[0][1],
        #as vectors#     u.Quantity(0.0, u.nanometer)
        #as vectors#    ],
        #as vectors#    [u.Quantity(0.0, u.nanometer),
        #as vectors#     u.Quantity(0.0, u.nanometer),
        #as vectors#     self.boundary[1][2] - self.boundary[0][2]
        #as vectors#    ],
        #as vectors#    ]
        #as vectors#[print(vec) for vec in boxvecs]
        #as vectors#self.topo.box_vectors = *boxvecs
        # parmed topology wants this for attr `box`
        # [ length length length angle angle angle ]
        boxarray = [
            self.boundary[1][0] - self.boundary[0][0],
            self.boundary[1][1] - self.boundary[0][1],
            self.boundary[1][2] - self.boundary[0][2],
            90 * u.degree,
            90 * u.degree,
            90 * u.degree
        ]

        self.topo.box = boxarray

    def get_sys_boundary(self):
        coords = self.coords.positions
        boundary = [
            [coords[0][0], coords[0][1], coords[0][2]],
            [coords[0][0], coords[0][1], coords[0][2]]
        ]

        for coord in coords[1:]:
            boundary[0][0] = min(
                boundary[0][0], coord[0]
            )
            boundary[1][0] = max(
                boundary[1][0], coord[0]
            )
            boundary[0][1] = min(
                boundary[0][1], coord[1]
            )
            boundary[1][1] = max(
                boundary[1][1], coord[1]
            )
            boundary[0][2] = min(
                boundary[0][2], coord[2]
            )
            boundary[1][2] = max(
                boundary[1][2], coord[2]
            )

        #print(boundary)
        return boundary

    def create_integrator(self, integrator="LangevinIntegrator"):
        self.integrator = getattr(mm, integrator)(*self.integrator_args)
        #self.integrator = mm.LangevinIntegrator(
        #    *self.integrator_args
        #    )

    def write_xmls(self, folder=None, prefix=None):
        print("Saving XML of files")
        if prefix is None:
            xmlprefix = self.systemfiles.sys_folder
            if folder:
                xmlprefix = os.path.join(xmlprefix, folder)
        else:
            xmlprefix = prefix

        if not os.path.exists(xmlprefix):
            os.makedirs(xmlprefix)

        for k,v in self.__class__._xmls.items():
            try:
                which = getattr(self, k)
                print("Writing: %s"%which)
                filelocation = os.path.join(xmlprefix, v)

                with open(filelocation, 'w') as f:
                    print("To Path: %s"%filelocation)
                    xml = mm.XmlSerializer.serialize(which)
                    f.write(xml)

            except AttributeError:
                pass
