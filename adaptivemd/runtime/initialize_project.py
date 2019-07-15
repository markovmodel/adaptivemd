
import yaml

from adaptivemd import Project, File, OpenMMEngine
from adaptivemd.analysis.pyemma import PyEMMAAnalysis


def initialize_project(p_name, sys_name=None, m_freq=None, p_freq=None, platform=None, features=None):

    dburl = os.environ.get("ADMD_DBURL", False)

    if dburl:

        logger.info("Set ADMD_DBURL to: " + dburl)
        Project.set_dburl(dburl)

    if p_name in Project.list():

        logger.info(
          "Project {0} exists, reading it from database"
          .format(p_name)
        )

        project = Project(p_name)

    elif not all([sys_name,m_freq,p_freq,platform]):

        raise ValueError(
          "Require paramters: [{0}] to initialize new project\nHave: {1}".format(
          "sys_name,m_freq,p_freq,platform", [sys_name,m_freq,p_freq,platform].__repr__())
        )

    else:

        project = Project(p_name)

        # Initialize w/ config file: 1 of multiple options
        # TODO add config filename argument
        configuration_file = 'configuration.cfg'

        project.initialize(configuration_file)

        f_name = '{0}.pdb'.format(sys_name)

        # FIXME add system specifications to configuration file
        f_base       = 'file:///$ADMD_MDSYSTEMS/{0}/'.format(sys_name)
        f_structure  = File(f_base + f_name).load()
        f_system     = File(f_base + 'system.xml').load()
        f_integrator = File(f_base + 'integrator.xml').load()

        sim_args = '-r -p {0}'.format(platform)

        if features is None:
            features = {'add_inverse_distances': {'select_Ca': None}}

        elif os.path.exists(features):
            features = yaml.safe_load(features)

        assert isinstance(features, (dict, list))

        engine = OpenMMEngine(f_system, f_integrator, f_structure, sim_args).named('openmm')

        m_freq = m_freq
        p_freq = p_freq

        engine.add_output_type('master', 'allatoms.dcd', stride=m_freq)
        engine.add_output_type('protein', 'protein.dcd', stride=p_freq, selection='protein')

        modeller = PyEMMAAnalysis(engine, 'protein', features).named('pyemma')

        project.generators.add(modeller)
        project.generators.add(engine)

        #[print(g) for g in project.generators]

    return project
