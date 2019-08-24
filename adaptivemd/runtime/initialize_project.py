
import os
import yaml
from pprint import pformat

from ..project import Project
from ..file import File
from ..engine.openmm import OpenMMEngine
from ..analysis.pyemma import PyEMMAAnalysis

from ..util import get_logger

logger = get_logger(__name__)

__all__ = ["initialize_project"]


def initialize_project(p_name, sys_name=None, m_freq=None, p_freq=None, platform=None, features=None, config=None):

    logger.info("This run is using config file: %s" % config)
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
        # TODO
        #if config:
        #    do-something-to-use-given-config

    elif not all([sys_name, m_freq, p_freq, platform]):

        raise ValueError(
          "Require paramters: [{0}] to initialize new project\nHave: {1}".format(
          "sys_name,m_freq,p_freq,platform", [sys_name,m_freq,p_freq,platform].__repr__())
        )

    else:

        project = Project(p_name)
        project.initialize(config)

        f_name = '{0}.pdb'.format(sys_name)

        # FIXME add system specifications to configuration file
        if sys_name in os.listdir(os.path.expandvars("$ADMD_MDSYSTEMS")):
            f_base = 'file:///$ADMD_MDSYSTEMS/{0}/'.format(sys_name)

        elif sys_name in os.listdir(os.path.join(os.path.expandvars("$ADMD_ADAPTIVEMD"), "examples/files")):
            f_base = 'file:///$ADMD_ADAPTIVEMD/examples/files/{0}/'.format(sys_name)

        else:
            raise ValueError( ("System name {} was not found in either $ADMD_MDSYSTEMS or "
                               "source package 'examples/files' directory".format(sys_name)) )

        f_structure  = File(f_base + f_name).load()
        f_system     = File(f_base + 'system.xml').load()
        f_integrator = File(f_base + 'integrator.xml').load()

        sim_args = '-v -p {0}'.format(platform)
        feat = None

        if features is None:
            feat = {'add_inverse_distances': {'select_Ca': None}}

        elif os.path.exists(features):
            with open(features, 'r') as _features:
                feat = yaml.safe_load(_features)

        logger.info(pformat(feat))
        assert isinstance(feat, (dict, list))

        engine = OpenMMEngine(f_system, f_integrator, f_structure, sim_args).named('openmm')

        m_freq = m_freq
        p_freq = p_freq

        engine.add_output_type('master', 'allatoms.dcd', stride=m_freq)
        engine.add_output_type('protein', 'protein.dcd', stride=p_freq, selection='protein')

        modeller = PyEMMAAnalysis(engine, 'protein', feat).named('pyemma')

        project.generators.add(modeller)
        project.generators.add(engine)

        #[print(g) for g in project.generators]

    return project
