from database import Database
from pprint import pprint
from utils import *
from resource_manager import ResourceManager

if __name__ == '__main__':

    db = Database(mongo_url='mongodb://user:user@two.radical-project.org:32769/', project='rp_testing_modeller_1')

    #print db.get_shared_files()

    #resource_desc_for_pilot = { 'resource': 'local.localhost',
    #                            'walltime'    : 30,
    #                            'cores'     : 2,
    #                            'project': ''
    #            }
    
    #rmgr = ResourceManager(resource_desc = resource_desc_for_pilot, db=db)
    #rmgr.submit_resource_request()

    #print db.get_source_files('65fc2c54-8b44-11e7-8783-00000000004a')

    #print db.get_file_destination('65fc2c54-8b44-11e7-8783-00000000006c')

    #gen = db.get_source_files(id='ba2b564e-8b3d-11e7-af58-00000000004a')

    #create_cud_from_task_def(db.get_tasks_definitions()[0])
    task_desc = db.get_task_descriptions(state='cancelled')
    #print len(task_desc)


    pprint(task_desc[0])
    #cuds = create_cud_from_task_def(task_desc, db, '/home/vivek')

    #cud = cuds[0]
    #print cud

    #for cud in cuds:
    #    print db.update_task_description_status(cud.name, 'cancelled')

    #task_desc = db.get_task_descriptions(state='cancelled')
    #print len(task_desc)
    #print task_desc
    #print db.update_task_description_status(cud.name, 'cancelled')
    #task_desc = db.get_task_descriptions(state='cancelled')
    #print task_desc


    #print cud.name
    #print cud.executable
    #print cud[0].arguments
    #print cud.input_staging
    #print cud[0].output_staging
    #print cud.cores


    #res_desc = db.get_resource_requirements()
    #pprint (res_desc)


    #confs = db.get_configurations()
    #pprint (confs)
