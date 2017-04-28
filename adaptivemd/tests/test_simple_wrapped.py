
import unittest

import os

from adaptivemd import Project
from adaptivemd import LocalResource

from adaptivemd import OpenMMEngine
from adaptivemd import PyEMMAAnalysis

from adaptivemd import File
from adaptivemd import WorkerScheduler

import mdtraj as md


class TestSimpleProject(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # init project and resource
        import tempfile
        cls.shared_path = tempfile.mkdtemp(prefix="adaptivemd")
        Project.delete('example-simple-1')
        cls.project = Project('example-simple-1')
        # --------------------------------------------------------------------------
        # CREATE THE RESOURCE
        #   the instance to know about the place where we run simulations
        # --------------------------------------------------------------------------
        resource = LocalResource(cls.shared_path)
        if os.getenv('CONDA_BUILD', False):
            # activate the conda build test environment for workers
            prefix = os.getenv('PREFIX')
            assert os.path.exists(prefix)
            resource.wrapper.pre.insert(0, 'source activate {prefix}'.format(prefix=prefix))
        else:
            # set the path for the workers to the path of the test interpreter.
            import sys
            resource.wrapper.pre.insert(0, 'PATH={python_path}:$PATH'
                                        .format(python_path=os.path.dirname(sys.executable)))
        cls.project.initialize(resource)
        return cls

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.shared_path)
        cls.project.delete('example-simple-1')
        os.chdir('/')

    def test(self):
        # --------------------------------------------------------------------------
        # CREATE THE ENGINE
        #   the instance to create trajectories
        # --------------------------------------------------------------------------

        pdb_file = File(
            'file://examples/files/alanine/alanine.pdb').named('initial_pdb').load()

        engine = OpenMMEngine(
            pdb_file=pdb_file,
            system_file=File('file://examples/files/alanine/system.xml').load(),
            integrator_file=File('file://examples/files/alanine/integrator.xml').load(),
            args='-r --report-interval 1 -p Reference --store-interval 1'
        ).named('openmm')

        # --------------------------------------------------------------------------
        # CREATE AN ANALYZER
        #   the instance that knows how to compute a msm from the trajectories
        # --------------------------------------------------------------------------

        modeller = PyEMMAAnalysis(
            engine=engine
        ).named('pyemma')

        self.project.generators.add(engine)
        self.project.generators.add(modeller)

        # --------------------------------------------------------------------------
        # CREATE THE CLUSTER
        #   the instance that runs the simulations on the resource
        # --------------------------------------------------------------------------
        traj_len = 5
        trajectory = self.project.new_trajectory(engine['pdb_file'], traj_len, engine)
        task = engine.run(trajectory)

        # self.project.queue(task)

        pdb = md.load('examples/files/alanine/alanine.pdb')

        # this part fakes a running worker without starting the worker process
        worker = WorkerScheduler(self.project.resource, verbose=True)
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
    unittest.main()
