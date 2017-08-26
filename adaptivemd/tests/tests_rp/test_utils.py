def test_process_resource_description():

    input_res_desc = {
                        "_id": "1e78cf80-8a96-11e7-af58-000000000062",
                        "_cls": "Resource",
                        "_obj_uuid": "1e78cf80-8a96-11e7-af58-000000000062",
                        "_dict": {
                                    "total_cpus": 32,
                                    "total_gpus": 1,
                                    "total_time": 30,
                                    "destination": "ornl.titan",
                                },
                        "_time": 1503776502
                    }

    output_res_desc = {

                        'resource': 'ornl.titan',
                        'walltime': 30
                        'cores': 32
    }
