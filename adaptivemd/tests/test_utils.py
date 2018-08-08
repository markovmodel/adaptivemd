import os
import json
import random
import string
import unittest
import adaptivemd.rp.utils as utils
import radical.pilot as rp
from adaptivemd.rp.database import Database

# Configuration Variables
#mongo_url = 'mongodb://user:user@two.radical-project.org:32770/'
mongo_url = 'mongodb://localhost:27017/'
project = 'rp_testing'

# Example JSON locations
directory = os.path.dirname(os.path.abspath(__file__))
conf_example = 'example-json/configuration-example.json'
res_example = 'example-json/resource-example.json'
task_example = 'example-json/task-example.json'
file_example = 'example-json/file-example.json'
gen_example = 'example-json/generator-example.json'
ptask_in_example = 'example-json/pythontask-input-example.json'


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """Random ID/String Generator"""
    return ''.join(random.choice(chars) for _ in range(size))


class TestUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize tests, just creates instance variables needed and the DB object.
        """
        super(TestUtils, cls).setUpClass()

        cls.db = Database(mongo_url=mongo_url,
                          project='{}_{}'.format(project, id_generator()))

        # Create Database and collections
        client = cls.db.client
        cls.store_name = "{}-{}".format(cls.db.store_prefix, cls.db.project)
        mongo_db = client[cls.store_name]
        tasks_col = mongo_db[cls.db.tasks_collection]
        configs_col = mongo_db[cls.db.configuration_collection]
        resources_col = mongo_db[cls.db.resource_collection]
        files_col = mongo_db[cls.db.file_collection]
        generators_col = mongo_db[cls.db.generator_collection]

        # Insert test documents
        with open('{}/{}'.format(directory, conf_example)) as json_data:
            data = json.load(json_data)
            for config_entry in data:
                configs_col.insert_one(config_entry)

        with open('{}/{}'.format(directory, res_example)) as json_data:
            data = json.load(json_data)
            for resource_entry in data:
                resources_col.insert_one(resource_entry)

        with open('{}/{}'.format(directory, file_example)) as json_data:
            data = json.load(json_data)
            for file_entry in data:
                files_col.insert_one(file_entry)

        with open('{}/{}'.format(directory, gen_example)) as json_data:
            data = json.load(json_data)
            for generator_entry in data:
                generators_col.insert_one(generator_entry)

        with open('{}/{}'.format(directory, task_example)) as json_data:
            # insert tasks
            data = json.load(json_data)
            for task_entry in data:
                tasks_col.insert_one(task_entry)

        cls.shared_path = '/home/test'
        cls.project = cls.db.project

    @classmethod
    def tearDownClass(cls):
        """Destroy the database since we don't need it anymore"""
        client = cls.db.client
        client.drop_database(cls.store_name)
        client.close()

    def test_get_input_staging_TrajectoryGenerationTask(self):
        """Test that the input staging directives are properly 
        generated for a TrajectoryGenerationTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-000000000124':
                task_desc = task
                break
        # Get each component of the task
        pre_task_details = task_desc['_dict'].get('pre', dict())
        main_task_details = task_desc['_dict'].get('_main', dict())
        
        staging_directives = utils.get_input_staging(
        task_details=pre_task_details, db=self.db, shared_path='/home/test', 
        project=self.db.project, break_after_non_dict=False)
        staging_directives.extend(utils.get_input_staging(
        task_details=main_task_details, db=self.db, shared_path='/home/test', 
        project=self.db.project, break_after_non_dict=True))
        
        actual = [
            {"action":"Link","source":"pilot:///alanine.pdb","target":"unit:///initial.pdb"},
            {"action":"Link","source":"pilot:///system.xml","target":"unit:///system.xml"},
            {"action":"Link","source":"pilot:///integrator.xml","target":"unit:///integrator.xml"},
            {"action":"Link","source":"pilot:///openmmrun.py","target":"unit:///openmmrun.py"}
        ]

        self.assertListEqual(staging_directives, actual)

    def test_get_input_staging_TrajectoryExtensionTask(self):
        """Test that the input staging directives are properly 
        generated for a TrajectoryGenerationTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '24888d76-219e-11e8-8f6d-000000000118':
                task_desc = task
                break
        # Get each component of the task
        pre_task_details = task_desc['_dict'].get('pre', dict())
        main_task_details = task_desc['_dict'].get('_main', dict())
        
        staging_directives = utils.get_input_staging(
        task_details=pre_task_details, db=self.db, shared_path='/home/test', 
        project=self.db.project, break_after_non_dict=False)
        staging_directives.extend(utils.get_input_staging(
        task_details=main_task_details, db=self.db, shared_path='/home/test', 
        project=self.db.project, break_after_non_dict=True))
        
        actual = [
            {"action":"Link","source":"pilot:///ntl9.pdb","target":"unit:///initial.pdb"},
            {"action":"Link","source":"pilot:///system-2.xml","target":"unit:///system-2.xml"},
            {"action":"Link","source":"pilot:///integrator-2.xml","target":"unit:///integrator-2.xml"},
            {"action":"Link","source":"pilot:///openmmrun.py","target":"unit:///openmmrun.py"},
            {"action":"Link","source":"/home/test//projects/test_analysis/trajs/00000000/","target":"unit:///source"}
        ]

        self.assertListEqual(staging_directives, actual)

    def test_get_input_staging_PythonTask(self):
        """Test that the input staging directives are properly 
        generated for a PythonTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-0000000000fe':
                task_desc = task
                break
        # Get each component of the task
        pre_task_details = task_desc['_dict'].get('pre', dict())
        main_task_details = task_desc['_dict'].get('_main', dict())
        
        staging_directives = utils.get_input_staging(
        task_details=pre_task_details, db=self.db, shared_path='/home/test', 
        project=self.db.project, break_after_non_dict=False)
        staging_directives.extend(utils.get_input_staging(
        task_details=main_task_details, db=self.db, shared_path='/home/test', 
        project=self.db.project, break_after_non_dict=True))

        actual = [
            {"action":"Link","source":"pilot:///_run_.py","target":"unit:///_run_.py"},
            {"action":"Link","source":"pilot:///alanine.pdb","target":"unit:///input.pdb"}
        ]
        self.assertListEqual(staging_directives, actual)

    def test_get_output_staging_TrajectoryGenerationTask(self):
        """Test that the output staging directives are properly generated for a TrajectoryGenerationTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-000000000124':
                task_desc = task
                break
        # Get each component of the task
        main_task_details = task_desc['_dict'].get('_main', dict())
        post_task_details = task_desc['_dict'].get('post', dict())

        staging_directives = utils.get_output_staging(
        task_desc=task_desc, task_details=post_task_details, db=self.db,
        shared_path='/home/test', project=self.db.project,
        continue_before_non_dict=False)
        staging_directives.extend(utils.get_output_staging(
        task_desc=task_desc, task_details=main_task_details, db=self.db,
        shared_path='/home/test', project=self.db.project,
        continue_before_non_dict=True))
        
        actual = [{"action":"Move","source":"traj/restart.npz",
            "target":"/home/test//projects/rp_testing_modeller_1/trajs/00000004//restart.npz"},
            {"action":"Move","source":"traj/master.dcd",
            "target":"/home/test//projects/rp_testing_modeller_1/trajs/00000004//master.dcd"},
            {"action":"Move","source":"traj/protein.dcd",
            "target":"/home/test//projects/rp_testing_modeller_1/trajs/00000004//protein.dcd"},
        ]
        
        self.assertListEqual(staging_directives, actual)

    def test_get_output_staging_TrajectoryExtensionTask(self):
        """Test that the output staging directives are properly generated for a TrajectoryGenerationTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '24888d76-219e-11e8-8f6d-000000000118':
                task_desc = task
                break
        # Get each component of the task
        main_task_details = task_desc['_dict'].get('_main', dict())
        post_task_details = task_desc['_dict'].get('post', dict())

        staging_directives = utils.get_output_staging(
        task_desc=task_desc, task_details=post_task_details, db=self.db,
        shared_path='/home/test', project=self.db.project,
        continue_before_non_dict=False)
        staging_directives.extend(utils.get_output_staging(
        task_desc=task_desc, task_details=main_task_details, db=self.db,
        shared_path='/home/test', project=self.db.project,
        continue_before_non_dict=True))

        actual = [
            {"action":"Move","source":"extension/protein.temp.dcd",
            "target":"extension/protein.dcd"},
            {"action":"Move","source":"extension/master.temp.dcd",
            "target":"extension/allatoms.dcd"},
            {"action":"Move","source":"extension/restart.npz",
            "target":"/home/test//projects/test_analysis/trajs/00000000//restart.npz"},
            {"action":"Move","source":"extension/allatoms.dcd",
            "target":"/home/test//projects/test_analysis/trajs/00000000//allatoms.dcd"},
            {"action":"Move","source":"extension/protein.dcd",
            "target":"/home/test//projects/test_analysis/trajs/00000000//protein.dcd"},
        ]
        
        self.assertListEqual(staging_directives, actual)

    def test_get_output_staging_PythonTask(self):
        """Test that the output staging directives are properly generated for a PythonTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-0000000000fe':
                task_desc = task
                break
        # Get each component of the task
        main_task_details = task_desc['_dict'].get('_main', dict())
        post_task_details = task_desc['_dict'].get('post', dict())

        staging_directives = utils.get_output_staging(
        task_desc=task_desc, task_details=post_task_details, db=self.db,
        shared_path='/home/test', project=self.db.project,
        continue_before_non_dict=False)
        staging_directives.extend(utils.get_output_staging(
        task_desc=task_desc, task_details=main_task_details, db=self.db,
        shared_path='/home/test', project=self.db.project,
        continue_before_non_dict=True))
        
        actual = [{
            "action": "Copy",
            "source": "output.json", 
            "target": "/home/test/projects/{}//models/model.0x4f01b528c6911e79eb20000000000feL.json".format(self.db.project)
        }]
        
        self.assertListEqual(staging_directives, actual)

    def test_get_commands_TrajectoryGenerationTask(self):
        """Test that the commands are properly captured for a TrajectoryGenerationTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-000000000124':
                task_desc = task
                break
        # Get each component of the task
        pre_task_details = task_desc['_dict'].get('pre', dict())
        main_task_details = task_desc['_dict'].get('_main', dict())
        post_task_details = task_desc['_dict'].get('post', dict())

        pre_commands = utils.get_commands(task_steps_list=pre_task_details, shared_path=self.shared_path, project=self.project)
        actual = [
            "source /home/test/venv/bin/activate",
            "mdconvert -o input.pdb -i 3 -t initial.pdb source/allatoms.dcd"
        ]

        self.assertListEqual(pre_commands, actual)

        main_commands = utils.get_commands(task_steps_list=main_task_details, shared_path=self.shared_path, project=self.project)
        actual = ["\nj=0\ntries=10\nsleep=1\n\ntrajfile=traj/allatoms.dcd\n\nwhile [ $j -le $tries ]; do if ! [ -s $trajfile ]; then python openmmrun.py -r --report-interval 1 -p CPU --types=\"{'protein':{'stride':1,'selection':'protein','name':null,'filename':'protein.dcd'},'master':{'stride':10,'selection':null,'name':null,'filename':'master.dcd'}}\" -t initial.pdb --length 100 traj/; fi; sleep 1; j=$((j+1)); done"]
        self.assertListEqual(main_commands, actual)

        post_commands = utils.get_commands(task_steps_list=post_task_details, shared_path=self.shared_path, project=self.project)
        actual = ["deactivate"]
        self.assertListEqual(post_commands, actual)

    def test_get_commands_TrajectoryExtensionTask(self):
        """Test that the commands are properly captured for a TrajectoryGenerationTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '24888d76-219e-11e8-8f6d-000000000118':
                task_desc = task
                break
        # Get each component of the task
        pre_task_details = task_desc['_dict'].get('pre', dict())
        main_task_details = task_desc['_dict'].get('_main', dict())
        post_task_details = task_desc['_dict'].get('post', dict())

        pre_commands = utils.get_commands(task_steps_list=pre_task_details, shared_path=self.shared_path, project=self.project)
        actual = [
            "module load python",
            "source /lustre/atlas/proj-shared/bip149/jrossyra/admdrp/admdrpenv/bin/activate"
        ]

        self.assertListEqual(pre_commands, actual)

        main_commands = utils.get_commands(task_steps_list=main_task_details, shared_path=self.shared_path, project=self.project)
        actual = ["\nj=0\ntries=10\nsleep=1\n\ntrajfile=extension/protein.dcd\n\nwhile [ $j -le $tries ]; do if ! [ -s $trajfile ]; then python openmmrun.py -r -p CPU --types=\"{'protein':{'stride':2,'selection':'protein','name':null,'filename':'protein.dcd'},'master':{'stride':10,'selection':null,'name':null,'filename':'allatoms.dcd'}}\" -s system-2.xml -i integrator-2.xml --restart /home/test//projects/test_analysis/trajs/00000000/restart.npz -t initial.pdb --length 200 extension/; fi; sleep 1; j=$((j+1)); done"]
        self.assertListEqual(main_commands, actual)

        post_commands = utils.get_commands(task_steps_list=post_task_details, shared_path=self.shared_path, project=self.project)
        actual = [
            "mdconvert -o extension/protein.temp.dcd source/protein.dcd extension/protein.dcd",
            "mdconvert -o extension/master.temp.dcd source/allatoms.dcd extension/allatoms.dcd",
            "deactivate"
        ]
        self.assertListEqual(post_commands, actual)
        
    def test_get_commands_PythonTask(self):
        """Test that the commands are properly captured for a PythonTask"""
        task_descriptions = self.db.get_task_descriptions()
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-0000000000fe':
                task_desc = task
                break
        # Get each component of the task
        pre_task_details = task_desc['_dict'].get('pre', dict())
        main_task_details = task_desc['_dict'].get('_main', dict())
        post_task_details = task_desc['_dict'].get('post', dict())

        pre_commands = utils.get_commands(task_steps_list=pre_task_details, shared_path=self.shared_path, project=self.project)
        actual = ["source /home/test/venv/bin/activate"]
        self.assertListEqual(pre_commands, actual)

        main_commands = utils.get_commands(task_steps_list=main_task_details, shared_path=self.shared_path, project=self.project)
        actual = ["python _run_.py"]
        self.assertListEqual(main_commands, actual)

        post_commands = utils.get_commands(task_steps_list=post_task_details, shared_path=self.shared_path, project=self.project)
        actual = ["deactivate"]
        self.assertListEqual(post_commands, actual)

    def test_get_environment_from_task_TrajectoryGenerationTask(self):
        """Test that the environment variables for the TrajectoryGenerationTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()
        
        # TrajectoryGenerationTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-000000000124':
                task_desc = task
                break

        environment = utils.get_environment_from_task(task_desc)
        actual = {"TEST1": "1", "TEST2": "2"}
        self.assertDictEqual(environment, actual)

    def test_get_environment_from_task_TrajectoryExtensionTask(self):
        """Test that the environment variables for the TrajectoryGenerationTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()
        
        # TrajectoryGenerationTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '24888d76-219e-11e8-8f6d-000000000118':
                task_desc = task
                break

        environment = utils.get_environment_from_task(task_desc)
        actual = {"OPENMM_CPU_THREADS": "1", "TEST1": "1", "TEST2": "2", "TEST3": "hello"}
        self.assertDictEqual(environment, actual)
    
    def test_get_environment_from_task_PythonTask(self):
        """Test that the environment variables for the PythonTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()

        # PythonTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-0000000000fe':
                task_desc = task
                break

        environment = utils.get_environment_from_task(task_desc)
        actual = {"TEST3": "3", "TEST4": "4"}
        self.assertDictEqual(environment, actual)

    def test_get_paths_from_task_TrajectoryGenerationTask(self):
        """Test that the paths variables for the TrajectoryGenerationTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()
        
        # TrajectoryGenerationTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-000000000124':
                task_desc = task
                break

        paths = utils.get_paths_from_task(task_desc)
        actual = [
            "/home/test/path1",
            "/home/test/path2"
        ]
        self.assertListEqual(paths, actual)

    def test_get_paths_from_task_TrajectoryExtensionTask(self):
        """Test that the paths variables for the TrajectoryGenerationTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()
        
        # TrajectoryGenerationTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '24888d76-219e-11e8-8f6d-000000000118':
                task_desc = task
                break

        paths = utils.get_paths_from_task(task_desc)
        actual = [
            "/home/test/path5",
            "/home/test/path6"
        ]
        self.assertListEqual(paths, actual)
    
    def test_get_paths_from_task_PythonTask(self):
        """Test that the paths variables for PythonTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()

        # PythonTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-0000000000fe':
                task_desc = task
                break

        paths = utils.get_paths_from_task(task_desc)
        actual = [
            "/home/test/path3",
            "/home/test/path4"
        ]
        self.assertListEqual(paths, actual)

    def test_get_executable_arguments_TrajectoryGenerationTask(self):
        """Test that the executable and its arguments for TrajectoryGenerationTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()
        
        # TrajectoryGenerationTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-000000000124':
                task_desc = task
                break

        exe, args = utils.get_executable_arguments(task_desc['_dict']['_main'], self.shared_path, self.project)
        actual_exe = 'python'
        actual_args = [
            "openmmrun.py", "-r", "--report-interval", "1",
            "-p", "CPU", "--types",
            "{'protein':{'stride':1,'selection':'protein','name':null,'filename':'protein.dcd'},'master':{'stride':10,'selection':null,'name':null,'filename':'master.dcd'}}",
            "-t", "initial.pdb", "--length", "100", "traj/"
        ]
        self.assertEqual(exe, actual_exe)
        for i in xrange(len(args)):
            self.assertEqual(args[i], actual_args[i])

    def test_get_executable_arguments_TrajectoryExtensionTask(self):
        """Test that the executable and its arguments for TrajectoryGenerationTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()
        
        # TrajectoryGenerationTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '24888d76-219e-11e8-8f6d-000000000118':
                task_desc = task
                break

        exe, args = utils.get_executable_arguments(task_desc['_dict']['_main'], self.shared_path, self.project)
        actual_exe = 'python'
        actual_args = [
            "openmmrun.py", "-r", "-p", "CPU", "--types",
            "{'protein':{'stride':2,'selection':'protein','name':null,'filename':'protein.dcd'},'master':{'stride':10,'selection':null,'name':null,'filename':'allatoms.dcd'}}",
            "-s", "system-2.xml", "-i", "integrator-2.xml", "--restart", "/home/test//projects/test_analysis/trajs/00000000/restart.npz",
            "-t", "initial.pdb", "--length", "200", "extension/"
        ]
        self.assertEqual(exe, actual_exe)
        for i in xrange(len(args)):
            self.assertEqual(args[i], actual_args[i])

    def test_get_executable_arguments_PythonTask(self):
        """Test that the executable and its arguments for PythonTask are properly captured"""
        task_descriptions = self.db.get_task_descriptions()

        # PythonTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == '04f01b52-8c69-11e7-9eb2-0000000000fe':
                task_desc = task
                break

        exe, args = utils.get_executable_arguments(task_desc['_dict']['_main'], self.shared_path, self.project)
        actual_exe = 'python'
        actual_args = ['_run_.py']
        self.assertEqual(exe, actual_exe)
        for i in xrange(len(args)):
            self.assertEqual(args[i], actual_args[i])

    def test_generate_pythontask_input(self):
        """Test that the input.json file and its contents is properly generated"""
        d1 = None
        with open('{}/{}'.format(directory, ptask_in_example)) as json_data:
            d1 = json.load(json_data)
        task = None
        task_descriptions = self.db.get_task_descriptions()
        for t in task_descriptions:
            if t['_cls'] == 'PythonTask':
                task = t
                break
        d2 = utils.generate_pythontask_input(
            db=self.db, shared_path='/home/example', task=task, project=self.db.project)
        self.assertDictEqual(d1, d2)

    def test_hex_to_id(self):
        """Test proper hex-to-id convertion"""
        hex_uuid = utils.hex_to_id("0x4f01b528c6911e79eb200000000003aL")
        actual = "04f01b52-8c69-11e7-9eb2-00000000003a"
        self.assertEquals(hex_uuid, actual)

    def test_resolve_pathholders(self):
        """Test our path expander/resolver"""
        # Direct Path
        exp_path = utils.resolve_pathholders("/some/path", shared_path='/home/test', project=self.db.project)
        actual = "/some/path"
        self.assertEquals(exp_path, actual)

        # Staging Path
        exp_path = utils.resolve_pathholders("staging:///some/path", shared_path='/home/test', project=self.db.project)
        actual = "pilot:///path" # SHOULD BE: actual = "pilot:///some/path"
        self.assertEquals(exp_path, actual)

        # Sandbox Path
        exp_path = utils.resolve_pathholders("sandbox:///some/path", shared_path='/home/test', project=self.db.project)
        actual = "/home/test//some/path"
        self.assertEquals(exp_path, actual)

        # File Path
        exp_path = utils.resolve_pathholders("file:///some/path.py", shared_path='/home/test', project=self.db.project)
        actual = "/some/path.py"
        self.assertEquals(exp_path, actual)

        # Projects Path
        exp_path = utils.resolve_pathholders("project:///some/path.py", shared_path='/home/test', project=self.db.project)
        actual = "/home/test/projects/{}//some/path.py".format(self.db.project)
        self.assertEquals(exp_path, actual)

    def test_generate_trajectorygenerationtask_generation_cud(self):
        """Test proper Compute Unit Description generation for TrajectoryGenerationTask"""
        task_descriptions = self.db.get_task_descriptions()

        # PythonTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == "04f01b52-8c69-11e7-9eb2-000000000124":
                task_desc = task
                break

        cud = utils.generate_trajectorygenerationtask_cud(task_desc, self.db, '/home/test', self.db.project)
        actual_cud = rp.ComputeUnitDescription()
        actual_cud.name = "04f01b52-8c69-11e7-9eb2-000000000124"
        actual_cud.environment = {
            "TEST1": "1",
            "TEST2": "2"
        }
        actual_cud.input_staging = [
            {"action":"Link","source":"pilot:///alanine.pdb","target":"unit:///initial.pdb"},
            {"action":"Link","source":"pilot:///system.xml","target":"unit:///system.xml"},
            {"action":"Link","source":"pilot:///integrator.xml","target":"unit:///integrator.xml"},
            {"action":"Link","source":"pilot:///openmmrun.py","target":"unit:///openmmrun.py"}
        ]
        actual_cud.pre_exec = [
            'mkdir -p traj',
            'mkdir -p extension',
            'source /home/test/venv/bin/activate',
            'mdconvert -o input.pdb -i 3 -t initial.pdb source/allatoms.dcd'
        ]
        actual_cud.executable = 'python'
        actual_cud.arguments = [
            "openmmrun.py", "-r", "--report-interval", "1",
            "-p", "CPU", "--types",
            "{'protein':{'stride':1,'selection':'protein','name':null,'filename':'protein.dcd'},'master':{'stride':10,'selection':null,'name':null,'filename':'master.dcd'}}",
            "-t", "initial.pdb", "--length", "100", "traj/"
        ]
        actual_cud.output_staging = [{"action":"Move","source":"traj/restart.npz",
            "target":"/home/test//projects/rp_testing_modeller_1/trajs/00000004//restart.npz"},
            {"action":"Move","source":"traj/master.dcd",
            "target":"/home/test//projects/rp_testing_modeller_1/trajs/00000004//master.dcd"},
            {"action":"Move","source":"traj/protein.dcd",
            "target":"/home/test//projects/rp_testing_modeller_1/trajs/00000004//protein.dcd"},
            ]
        actual_cud.post_exec = ['deactivate']

        actual_cud.cpu_process_type  = 'POSIX'
        #actual_cud.gpu_process_type  = 'POSIX'
        actual_cud.cpu_thread_type   = 'POSIX'
        #actual_cud.gpu_thread_type   = 'CUDA'
        actual_cud.cpu_processes = 1
        #actual_cud.gpu_processes = 1
        actual_cud.cpu_threads   = 1
        #actual_cud.gpu_threads   = 1

        # compare all parts of the cuds
        self.maxDiff = None
        self.assertEquals(cud.name, actual_cud.name)
        self.assertDictEqual(cud.environment, actual_cud.environment)
        self.assertListEqual(cud.input_staging, actual_cud.input_staging)
        self.assertListEqual(cud.pre_exec, actual_cud.pre_exec)
        self.assertEquals(cud.executable, actual_cud.executable)
        self.assertListEqual(cud.arguments, actual_cud.arguments)
        self.assertListEqual(cud.output_staging, actual_cud.output_staging)
        self.assertListEqual(cud.post_exec, actual_cud.post_exec)

        self.assertEquals(cud.cpu_process_type, actual_cud.cpu_process_type)
        self.assertEquals(cud.cpu_thread_type, actual_cud.cpu_thread_type)
        self.assertEquals(cud.cpu_processes, actual_cud.cpu_processes)
        self.assertEquals(cud.cpu_threads, actual_cud.cpu_threads)

    def test_generate_trajectorygenerationtask_extension_cud(self):
        """Test proper Compute Unit Description generation for TrajectoryExtensionTask"""
        task_descriptions = self.db.get_task_descriptions()

        # PythonTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == "24888d76-219e-11e8-8f6d-000000000118":
                task_desc = task
                break

        cud = utils.generate_trajectorygenerationtask_cud(task_desc, self.db, self.shared_path, self.project)
        actual_cud = rp.ComputeUnitDescription()
        actual_cud.name = "24888d76-219e-11e8-8f6d-000000000118"
        actual_cud.environment = {
            "OPENMM_CPU_THREADS": "1",
            "TEST1": "1",
            "TEST2": "2",
            "TEST3": "hello"
        }
        actual_cud.input_staging = [
            {"action":"Link","source":"pilot:///ntl9.pdb","target":"unit:///initial.pdb"},
            {"action":"Link","source":"pilot:///system-2.xml","target":"unit:///system-2.xml"},
            {"action":"Link","source":"pilot:///integrator-2.xml","target":"unit:///integrator-2.xml"},
            {"action":"Link","source":"pilot:///openmmrun.py","target":"unit:///openmmrun.py"},
            {"action":"Link","source":"/home/test//projects/test_analysis/trajs/00000000/","target":"unit:///source"}
        ]
        actual_cud.pre_exec = [
            'mkdir -p traj',
            'mkdir -p extension',
            "module load python",
            "source /lustre/atlas/proj-shared/bip149/jrossyra/admdrp/admdrpenv/bin/activate"
        ]
        actual_cud.executable = 'python'
        actual_cud.arguments = [
            "openmmrun.py", "-r", "-p", "CPU", "--types",
            "{'protein':{'stride':2,'selection':'protein','name':null,'filename':'protein.dcd'},'master':{'stride':10,'selection':null,'name':null,'filename':'allatoms.dcd'}}",
            "-s", "system-2.xml", "-i", "integrator-2.xml", "--restart", "/home/test//projects/test_analysis/trajs/00000000/restart.npz",
            "-t", "initial.pdb", "--length", "200", "extension/"
        ]
        actual_cud.output_staging = [
            {"action":"Move","source":"extension/protein.temp.dcd",
            "target":"extension/protein.dcd"},
            {"action":"Move","source":"extension/master.temp.dcd",
            "target":"extension/allatoms.dcd"},
            {"action":"Move","source":"extension/restart.npz",
            "target":"/home/test//projects/test_analysis/trajs/00000000//restart.npz"},
            {"action":"Move","source":"extension/allatoms.dcd",
            "target":"/home/test//projects/test_analysis/trajs/00000000//allatoms.dcd"},
            {"action":"Move","source":"extension/protein.dcd",
            "target":"/home/test//projects/test_analysis/trajs/00000000//protein.dcd"},
        ]
        actual_cud.post_exec = [
            "mdconvert -o extension/protein.temp.dcd source/protein.dcd extension/protein.dcd",
            "mdconvert -o extension/master.temp.dcd source/allatoms.dcd extension/allatoms.dcd",
            "deactivate"
        ]
        actual_cud.cpu_process_type  = 'POSIX'
        actual_cud.gpu_process_type  = 'POSIX'
        actual_cud.cpu_thread_type   = 'POSIX'
        actual_cud.gpu_thread_type   = 'CUDA'
        actual_cud.cpu_processes = 1
        actual_cud.gpu_processes = 1
        actual_cud.cpu_threads   = 1
        actual_cud.gpu_threads   = 1


        # compare all parts of the cuds
        self.maxDiff = None
        self.assertEquals(cud.name, actual_cud.name)
        self.assertDictEqual(cud.environment, actual_cud.environment)
        self.assertListEqual(cud.input_staging, actual_cud.input_staging)
        self.assertListEqual(cud.pre_exec, actual_cud.pre_exec)
        self.assertEquals(cud.executable, actual_cud.executable)
        self.assertListEqual(cud.arguments, actual_cud.arguments)
        self.assertListEqual(cud.output_staging, actual_cud.output_staging)
        self.assertListEqual(cud.post_exec, actual_cud.post_exec)

        self.assertEquals(cud.cpu_process_type, actual_cud.cpu_process_type)
        self.assertEquals(cud.cpu_thread_type, actual_cud.cpu_thread_type)
        self.assertEquals(cud.cpu_processes, actual_cud.cpu_processes)
        self.assertEquals(cud.cpu_threads, actual_cud.cpu_threads)

    def test_generate_pythontask_cud(self):
        """Test proper Compute Unit Description generation for PythonTask"""
        task_descriptions = self.db.get_task_descriptions()

        # PythonTask
        task_desc = dict()
        for task in task_descriptions:
            if task['_id'] == "04f01b52-8c69-11e7-9eb2-0000000000fe":
                task_desc = task
                break

        # Get the input.json example
        with open('{}/{}'.format(directory, ptask_in_example)) as json_data:
            inpu_json_data = json.load(json_data)

        cud = utils.generate_pythontask_cud(task_desc, self.db, '/home/example', self.db.project)
        actual_cud = rp.ComputeUnitDescription()
        actual_cud.name = "04f01b52-8c69-11e7-9eb2-0000000000fe"
        actual_cud.environment = {
            "TEST3": "3",
            "TEST4": "4"
        }
        actual_cud.input_staging = [
            {"action":"Link","source":"pilot:///_run_.py","target":"unit:///_run_.py"},
            {"action":"Link","source":"pilot:///alanine.pdb","target":"unit:///input.pdb"}
        ]
        actual_cud.pre_exec = [
            'mkdir -p traj',
            'mkdir -p extension',
            'echo \'{}\' > \'{}\''.format(json.dumps(inpu_json_data['contents']), inpu_json_data['target']), # stage input.json
            "source /home/test/venv/bin/activate"
        ]
        actual_cud.executable = 'python'
        actual_cud.arguments = ['_run_.py']
        actual_cud.output_staging = [{
            "action": "Copy",
            "source": "output.json", 
            "target": "/home/example/projects/{}//models/model.0x4f01b528c6911e79eb20000000000feL.json".format(self.db.project)
        }]
        actual_cud.post_exec = ["deactivate"]

        actual_cud.cpu_process_type  = 'POSIX'
        actual_cud.gpu_process_type  = 'POSIX'
        actual_cud.cpu_thread_type   = 'POSIX'
        actual_cud.gpu_thread_type   = 'CUDA'
        actual_cud.cpu_processes = 10
        actual_cud.gpu_processes = 1
        actual_cud.cpu_threads   = 1
        actual_cud.gpu_threads   = 1

        # compare all parts of the cuds
        self.maxDiff = None
        self.assertEquals(cud.name, actual_cud.name)
        self.assertDictEqual(cud.environment, actual_cud.environment)
        self.assertListEqual(cud.input_staging, actual_cud.input_staging)
        self.assertListEqual(cud.pre_exec, actual_cud.pre_exec)
        self.assertEquals(cud.executable, actual_cud.executable)
        self.assertListEqual(cud.arguments, actual_cud.arguments)
        self.assertListEqual(cud.output_staging, actual_cud.output_staging)
        self.assertListEqual(cud.post_exec, actual_cud.post_exec)

        self.assertEquals(cud.cpu_process_type, actual_cud.cpu_process_type)
        self.assertEquals(cud.cpu_thread_type, actual_cud.cpu_thread_type)
        self.assertEquals(cud.cpu_processes, actual_cud.cpu_processes)
        self.assertEquals(cud.cpu_threads, actual_cud.cpu_threads)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUtils)
    unittest.TextTestRunner(verbosity=2).run(suite)
