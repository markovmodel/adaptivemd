from adaptivemd.rp.utils import *
import radical.pilot as rp


def test_resolve_pathholders():

    raw_path = '/home/vivek/test.txt'
    processed_path = resolve_pathholders(raw_path,'/home/vivek')
    expected_path = raw_path
    assert expected_path == processed_path

    raw_path = 'staging:///test.txt'
    processed_path = resolve_pathholders(raw_path, '/home/vivek')
    expected_path = 'pilot:///test.txt'
    assert expected_path == processed_path

    raw_path = 'sandbox:///abc/xyc/test.txt'
    process_path = resolve_pathholders(raw_path, '/home/vivek')
    expected_path = '/home/vivek//abc/xyz/test.txt'
    assert expected_path == processed_path



def test_process_resource_description():

    input_res_desc = [{
                        "_id": "1e78cf80-8a96-11e7-af58-000000000062",
                        "_cls": "Resource",
                        "_obj_uuid": "1e78cf80-8a96-11e7-af58-000000000062",
                        "_dict": {
                                    "total_cpus": 32,
                                    'name': None,
                                    "total_gpus": 1,
                                    "total_time": 30,
                                    "destination": "ornl.titan",
                                },
                        "_time": 1503776502,
                        'name': None
                    }]

    expected_output_res_desc = [{

                        "total_cpus": 32,
                        "total_gpus": 1,
                        "total_time": 30,
                        "resource": "ornl.titan"
                        }]

    actual_output_res_desc = process_resource_requirements(input_res_desc)


    assert set(actual_output_res_desc[0].keys()) == set(["total_cpus", "total_gpus", "total_time", "resource"])
    
    assert actual_output_res_desc[0]['total_cpus'] == expected_output_res_desc[0]['total_cpus']
    assert actual_output_res_desc[0]['total_gpus'] == expected_output_res_desc[0]['total_gpus']
    assert actual_output_res_desc[0]['total_time'] == expected_output_res_desc[0]['total_time']
    assert actual_output_res_desc[0]['resource'] == expected_output_res_desc[0]['resource']


def test_process_configurations():

    input_conf_desc = [{
                            "_id": "1e78cf80-8a96-11e7-af58-000000000034",
                            "_cls": "Configuration",
                            "_obj_uuid": "1e78cf80-8a96-11e7-af58-000000000034",
                            "_dict": {
                                        "shared_path": "$HOME/adaptivemd/",
                                        "allocation": "some-allocation-id",
                                        "resource_name": "ornl.titan",
                                        "queues": ['queue1', 'queue2'],
                                        "cores_per_node": 1,
                                        "name": "titan-1"
                                    },
                            "_time": 1503776431,
                            "name": "titan-1"
                        }]


    expected_output_conf_desc = [

                            {
                                "resource": "ornl.titan",
                                "queue": "queue1",
                                "project": "some-allocation-id",
                                "shared_path": "$HOME/adaptivemd/"
                            },
                            {
                                "resource": "ornl.titan",
                                "queue": "queue2",
                                "project": "some-allocation-id",
                                "shared_path": "$HOME/adaptivemd/"
                            }

                        ]

    actual_output_conf_desc = process_configurations(input_conf_desc)

    assert set(actual_output_conf_desc[0].keys()) == set(expected_output_conf_desc[0].keys())
    assert set(actual_output_conf_desc[1].keys()) == set(expected_output_conf_desc[1].keys())

    assert actual_output_conf_desc[0]['resource']       == expected_output_conf_desc[0]['resource']
    assert actual_output_conf_desc[0]['queue']          == expected_output_conf_desc[0]['queue']
    assert actual_output_conf_desc[0]['project']        == expected_output_conf_desc[0]['project']
    assert actual_output_conf_desc[0]['shared_path']    == expected_output_conf_desc[0]['shared_path']

    assert actual_output_conf_desc[1]['resource']       == expected_output_conf_desc[1]['resource']
    assert actual_output_conf_desc[1]['queue']          == expected_output_conf_desc[1]['queue']
    assert actual_output_conf_desc[1]['project']        == expected_output_conf_desc[1]['project']
    assert actual_output_conf_desc[1]['shared_path']    == expected_output_conf_desc[1]['shared_path']


def test_process_task_descriptions():

    input_task_desc =   {
                            "_id": "fc2a421c-89e4-11e7-af58-0000000000da",
                            "_cls": "TrajectoryGenerationTask",
                            "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000da",
                            "_dict": {
                                "_main": [
                                        {
                                            "_cls": "Link",
                                            "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000de",
                                            "_dict": {
                                                "source": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-000000000072",
                                                    "_dict": {
                                                        "location": "staging:///alanine.pdb",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                },
                                                "target": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000e0",
                                                    "_dict": {
                                                        "location": "initial.pdb",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            "_cls": "Link",
                                            "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000e4",
                                            "_dict": {
                                                "source": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-000000000078",
                                                    "_dict": {
                                                        "location": "staging:///system.xml",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                },
                                                "target": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000e6",
                                                    "_dict": {
                                                        "location": "system.xml",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            "_cls": "Link",
                                            "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000ea",
                                            "_dict": {
                                                "source": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-00000000007e",
                                                    "_dict": {
                                                        "location": "staging:///integrator.xml",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                },
                                                "target": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000ec",
                                                    "_dict": {
                                                        "location": "integrator.xml",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            "_cls": "Link",
                                            "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000f0",
                                            "_dict": {
                                                "source": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-000000000084",
                                                    "_dict": {
                                                        "location": "staging:///openmmrun.py",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                },
                                                "target": {
                                                    "_cls": "File",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000f2",
                                                    "_dict": {
                                                        "location": "openmmrun.py",
                                                        "resource": None,
                                                        "_file": None
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            "_cls": "Touch",
                                            "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000f6",
                                            "_dict": {
                                                "source": {
                                                    "_cls": "Trajectory",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000f4",
                                                    "_dict": {
                                                        "length": 100,
                                                        "location": "traj/",
                                                        "frame": {
                                                            "_hex_uuid": "0xfc2a421c89e411e7af5800000000003a",
                                                            "_store": "files"
                                                        },
                                                    "resource": None,
                                                    "_file": None
                                                    }
                                                }
                                            }
                                        },
                                        "\nj=0\ntries=10\nsleep=1\n\ntrajfile=traj/allatoms.dcd\n\nwhile [ $j -le $tries ]; do if ! [ -s $trajfile ]; then python openmmrun.py -r --report-interval 1 -p CPU --types=\"{'master':{'selection':None,'filename':'master.dcd','stride':10},'protein':{'selection':'protein','filename':'protein.dcd','stride':1}}\" -t worker://initial.pdb --length 100 worker://traj/; fi; sleep 1; j=$((j+1)); done",
                                        {
                                            "_cls": "Move",
                                            "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000f8",
                                            "_dict": {
                                                "source": {
                                                    "_cls": "Trajectory",
                                                    "_obj_uuid": "fc2a421c-89e4-11e7-af58-0000000000f4",
                                                    "_dict": {
                                                        "length": 100,
                                                        "location": "traj/",
                                                        "frame": {
                                                            "_hex_uuid": "0xfc2a421c89e411e7af5800000000003a",
                                                            "_store": "files"
                                                        },
                                                    "resource": None,
                                                    "_file": None
                                                    }
                                                },
                                                "target": {
                                                "_hex_uuid": "0xfc2a421c89e411e7af58000000000096",
                                                "_store": "files"
                                                }
                                            }
                                        }
                                    ],
                                "_add_paths": [],
                                "_environment": {},
                                "stdout": None,
                                "stderr": None,
                                "restartable": None,
                                "cleanup": None,
                                'est_exec_time': 5,
                                'resource_name': ['ornl.titan'],
                                'resource_requirements': {
                                                            'cpu_threads': 1,
                                                            'gpu_contexts': 0,
                                                            'mpi_rank': 0
                                                        },
                                "generator": {
                                  "_hex_uuid": "0xfc2a421c89e411e7af5800000000006a",
                                  "_store": "generators"
                                },
                                "dependencies": None,
                                "state": "created",
                                "worker": None,
                                "trajectory": {
                                  "_hex_uuid": "0xfc2a421c89e411e7af58000000000096",
                                  "_store": "files"
                                }
                            },
                        "_time": 1503700753,
                        "state": "created",
                        "worker": None,
                        "stderr": None,
                        "stdout": None
                    }
                


    expected_output_task_desc = rp.ComputeUnitDescription()

    expected_output_task_desc.name = input_task_desc['_id']
    expected_output_task_desc.executable = 'python'
    expected_output_task_desc.arguments = [ 'openmmrun.py','-r', 
                                            '--report-interval' ,'1',
                                            '-p', 'CPU', 
                                            '--types="{\'master\':{\'selection\':None,\'filename\':\'master.dcd\',\'stride\':10},\'protein\':{\'selection\':\'protein\',\'filename\':\'protein.dcd\',\'stride\':1}}"']
    expected_output_task_desc.input_staging = [
                                                {
                                                    'source': '$HOME/vivek/workers/staging_area/alanine.pdb',
                                                    'action': rp.LINK,
                                                    'target': 'initial.pdb'
                                                },
                                                {
                                                    'source': '$HOME/vivek/workers/staging_area/system.xml',
                                                    'action': rp.LINK,
                                                    'target': 'system.xml'
                                                },
                                                {
                                                    'source': '$HOME/vivek/workers/staging_area/integrator.xml',
                                                    'action': rp.LINK,
                                                    'target': 'integrator.xml'
                                                },
                                                
                                                {
                                                    'source': '$HOME/vivek/workers/staging_area/openmmrun.py',
                                                    'action': rp.LINK,
                                                    'target': 'openmmrun.py'
                                                },
                                            ]

    pprint(expected_output_task_desc.input_staging)

    expected_output_task_desc.output_staging = []
    expected_output_task_desc.cores = 16

    

    actual_output_task_desc = create_cud_from_task_def(input_task_desc, '$HOME/vivek')


    pprint(actual_output_task_desc.input_staging)

    assert actual_output_task_desc.name == expected_output_task_desc.name
    assert actual_output_task_desc.executable == expected_output_task_desc.executable
    assert actual_output_task_desc.arguments == expected_output_task_desc.arguments
    assert actual_output_task_desc.input_staging == expected_output_task_desc.input_staging
    assert actual_output_task_desc.output_staging == expected_output_task_desc.output_staging
    assert actual_output_task_desc.cores == expected_output_task_desc.cores
