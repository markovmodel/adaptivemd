
import os
import unittest

from adaptivemd import File, WorkerScheduler, Worker
from adaptivemd import LocalResource
from adaptivemd import OpenMMEngine
from adaptivemd import Project
from adaptivemd import PyEMMAAnalysis


def start_local_worker(proj_name):
    import subprocess, sys, os
    path = os.path.dirname(sys.executable) + ':' + os.environ['PATH']
    env = dict(os.environ)
    env['PATH'] = path
    p = subprocess.Popen(['adaptivemdworker', proj_name], env=env)
    print("started worker as subprocess from steering program")
    return p


class TestSimpleStrategy(unittest.TestCase):

    f_base = None

    @classmethod
    def setUpClass(cls):
        # init project and resource
        import tempfile
        cls.proj_name = 'example-strategy-1'
        cls.shared_path = tempfile.mkdtemp(prefix="adaptivemd")
        Project.delete(cls.proj_name)
        cls.project = Project(cls.proj_name)
        # ----------------------------------------------------------------------
        # CREATE THE RESOURCE
        #   the instance to know about the place where we run simulations
        # ----------------------------------------------------------------------
        resource = LocalResource(cls.shared_path)
        if os.getenv('CONDA_BUILD', False):
            # activate the conda build test environment for workers

            cls.f_base = 'examples/files/alanine/'
            prefix = os.getenv('PREFIX')
            assert os.path.exists(prefix)
            resource.wrapper.pre.insert(0,
                'source activate {prefix}'.format(prefix=prefix))

            # TODO why does test_simple_wrapper not
            #      have a chdir to ci test environment?
            test_tmp = prefix + '/../test_tmp/'
            if os.getcwd() is not test_tmp:
                os.chdir(test_tmp)
        else:
            # set the path for the workers to the path of the test interpreter.
            import sys

            cls.f_base = '../../examples/files/alanine/'
            resource.wrapper.pre.insert(0, 'PATH={python_path}:$PATH'
                .format(python_path=os.path.dirname(sys.executable)))

        cls.project.initialize(resource)
        cls.worker_process = start_local_worker(cls.proj_name)
        return cls

    @classmethod
    def tearDownClass(cls):

        cls.worker_process.terminate()

        import shutil
        shutil.rmtree(cls.shared_path)
        cls.project.delete(cls.proj_name)
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
            args='-r --report-interval 1 -p Reference --store-interval 1 -v'
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

        def strategy(loops=2, trajs_per_loop=2, length=3):
            initial_traj = self.project.new_trajectory(frame=pdb_file, length=length)
            task = engine.run(initial_traj)
            self.project.queue(task)
            yield task.is_done

            for loop in range(loops):
                # submit some trajectory tasks
                trajectories = self.project.new_ml_trajectory(engine=engine, length=length, number=trajs_per_loop)
                tasks = tuple(map(engine.run, trajectories))
                self.project.queue(tasks)
                print("queued %s tasks" % len(tasks))

                # continue if ALL of the tasks are done (can be failed)
                yield [task.is_done for task in tasks]

                # submit a model job
                task = modeller.execute(list(self.project.trajectories))
                self.project.queue(task)
                print("queued modeller task")

                # when it is done do next loop
                yield task.is_done

        # TODO worker/MD running in subprocess thread horribly slow
        #      - fix somehow and keep 2,2 for loops, trajs
        n_loops = 1#2
        trajs_per_loop = 1#2
        self.project.add_event(strategy(loops=n_loops, trajs_per_loop=trajs_per_loop))
        self.project.run()
        self.project.wait_until(self.project.on_ntraj(n_loops*trajs_per_loop))

        self.assertEqual(len(list(self.project.trajectories)), n_loops*trajs_per_loop)
        self.project.close()

if __name__ == '__main__':
    unittest.main()
