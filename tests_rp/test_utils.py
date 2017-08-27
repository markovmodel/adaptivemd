from adaptivemd.rp.utils import *


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

    expected_output_res_desc = {

                        "total_cpus": 32,
                        "total_gpus": 1,
                        "total_time": 30,
                        "resource": "ornl.titan"
    }

    actual_output_res_desc = process_resource_description(input_res_desc)


    assert set(actual_output_res_desc[0].keys()) == set(["total_cpus", "total_gpus", "total_time", "resource"])
    
    assert actual_output_res_desc[0]['total_cpus'] == expected_output_res_desc['total_cpus']
    assert actual_output_res_desc[0]['total_gpus'] == expected_output_res_desc['total_gpus']
    assert actual_output_res_desc[0]['total_time'] == expected_output_res_desc['total_time']
    assert actual_output_res_desc[0]['resource'] == expected_output_res_desc['resource']

'''
def test_process_configurations():

    input_conf_desc = [{
                            "_id": "1e78cf80-8a96-11e7-af58-000000000034",
                            "_cls": "Configuration",
                            "_obj_uuid": "1e78cf80-8a96-11e7-af58-000000000034",
                            "_dict": {
                                        "shared_path": "$HOME/adaptivemd/",
                                        "allocation": "some-allocation-id",
                                        "resource_name": "titan",
                                        "queues": ['queue1', 'queue2'],
                                        "cores_per_node": 1,
                                        "name": "titan-1"
                                    },
                            "_time": 1503776431,
                            "name": "titan-1"
                        }]


    expected_conf_desc =
'''