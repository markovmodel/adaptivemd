
import unittest

import os

from adaptivemd import Project
from adaptivemd import OpenMMEngine
from adaptivemd import File

from adaptivemd import PyEMMAAnalysis
from adaptivemd import WorkerScheduler
import mdtraj as md


class TestSimpleProject(unittest.TestCase):

    '''
    Include information that coordinates the test as class attributes

    f_base :
                base path for directory structure
    '''

    f_base = None
    d_home = os.path.dirname(os.path.realpath(__file__))

    @classmethod
    def setUpClass(cls):
        '''
        Operations that configure the test environment
        ----------------------------------------------

            env :
                    determine if local or in integration environment

            pkg :
                    object imports and coordination

            cfg :
                    object instantiation and building
                    one-time operations that set up for test

        '''

        # init project and resource
        import tempfile
        cls.shared_path = tempfile.mkdtemp(prefix="adaptivemd")
        Project.delete('test-skeleton')
        cls.project = Project('test-skeleton')
        cls.project.initialize({'shared_path':cls.shared_path})
        # ----------------------------------------------------------------------
        # CREATE THE RESOURCE
        #   the instance to know about the place where we run simulations
        # ----------------------------------------------------------------------
        if os.getenv('CONDA_BUILD', False):

            # activate the conda build test environment
            cls.f_base = 'examples/files/alanine/'
            prefix = os.getenv('PREFIX')
            assert os.path.exists(prefix)

            cls.project.configuration.wrapper.pre.insert(0,
                'source activate {prefix}'.format(prefix=prefix))

            # TODO why does test_simple_wrapped not
            #      have a chdir to ci test environment?
            # TODO this is dealing in relative paths
            #      --> should check cwd based on absolute path
            test_tmp = prefix + '/../test_tmp/'
            if os.getcwd() is not test_tmp:
                os.chdir(test_tmp)

        else:
            # set the path for the workers to the path of the test interpreter.
            import sys

            cls.f_base = '../../examples/files/alanine/'
            cls.project.configuration.wrapper.pre.insert(0, 'PATH={python_path}:$PATH'
                .format(python_path=os.path.dirname(sys.executable)))

        return cls

    @classmethod
    def tearDownClass(cls):
        '''
        Cleanup operations that move our session to the directory we started at
        and cleanup the files and folders we created
        '''
        import shutil
        shutil.rmtree(cls.shared_path)
        cls.project.delete('example-simple-1')
        os.chdir('/')

    def test(self):
        # ----------------------------------------------------------------------
        # CREATE THE ENGINE
        #   the instance to create trajectories
        # ----------------------------------------------------------------------



        pdb_file = File('file://{0}alanine.pdb'.format(
            self.f_base)).named('initial_pdb').load()

        engine = OpenMMEngine(
            pdb_file=pdb_file,
            system_file=File('file://{0}system.xml'.format(
                self.f_base)).load(),
            integrator_file=File('file://{0}integrator.xml'.format(
                self.f_base)).load(),
            args='-r --report-interval 1 -p CPU --store-interval 1'
        ).named('openmm')

        # ----------------------------------------------------------------------
        # CREATE AN ANALYZER
        #   the instance that knows how to compute a msm from the trajectories
        # ----------------------------------------------------------------------

        modeller = PyEMMAAnalysis(
            engine=engine
        ).named('pyemma')

        self.project.generators.add(engine)
        self.project.generators.add(modeller)

        # ----------------------------------------------------------------------
        # CREATE THE CLUSTER
        #   the instance that runs the simulations on the resource
        # ----------------------------------------------------------------------
        traj_len = 1
        trajectory = self.project.new_trajectory(engine['pdb_file'], traj_len, engine)
        task = engine.run(trajectory)

        # self.project.queue(task)

        pdb = md.load('{0}alanine.pdb'.format(self.f_base))

        # this part fakes a running worker without starting the worker process
        worker = WorkerScheduler(self.project.configuration, verbose=True)
        worker.enter(self.project)

        worker.submit(task)

        self.assertEqual(len(self.project.trajectories), 0)

        while not task.is_done():
            worker.advance()

        try:
            assert(len(self.project.trajectories) == 1)
        except AssertionError:
            print("stderr from worker task: \n%s" % task.stderr)
            print("stdout from worker task: \n%s" % task.stdout)
            raise
        print("stdout of worker:\n%s" % task.stdout)

        # FIXME: the worker space is cleared, so the trajectory paths are not valid anymore.
        # traj_path = os.path.join(
        #     worker.path,
        #     'workers',
        #     'worker.' + hex(task.__uuid__),
        #     worker.replace_prefix(self.project.trajectories.one.url)
        # )
        # this is a workaround, but assumes that sandbox:// lives on the same fs.
        traj_path = os.path.join(self.shared_path, self.project.trajectories.one.dirname[1:], 'output.dcd')

        assert(os.path.exists(traj_path)), traj_path

        # go back to the place where we ran the test
        traj = md.load(traj_path, top=pdb)

        assert(len(traj) == traj_len + 1), len(traj)

        # well, we have a 100 step trajectory which matches the size of the initial PDB
        # that is a good sign

        # extend the trajectory by 10
        task2 = task.extend(10)

        worker.submit(task2)

        while not task2.is_done():
            worker.advance()

        # should still be one, since we have the same trajectory
        assert(len(self.project.trajectories) == 1)

        traj = md.load(traj_path, top=pdb)

        self.assertEqual(len(traj), traj_len + 10 + 1)

        # after extension it is traj_len + 10 frames. Excellent

        self.project.close()

if __name__ == '__main__':
    '''
    Rigid structure to call run of unit test
    '''

    unittest.main()

