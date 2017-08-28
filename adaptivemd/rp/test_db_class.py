from database import Database
from pprint import pprint
from utils import *

if __name__ == '__main__':

    db = Database(mongo_url='mongodb://user:user@two.radical-project.org:32769/', project='rp_testing_3')
    

    print db.get_shared_files()

    #print db.get_source_files('65fc2c54-8b44-11e7-8783-00000000004a')

    #print db.get_file_destination('65fc2c54-8b44-11e7-8783-00000000006c')

    #gen = db.get_source_files(id='ba2b564e-8b3d-11e7-af58-00000000004a')

    #create_cud_from_task_def(db.get_tasks_definitions()[0])
    #task_desc = db.get_task_descriptions(state='running')

    #pprint(task_desc[0])
    #cud = create_cud_from_task_def(task_desc[0], db, '/home/vivek')
    #print cud.name
    #print cud.executable
    #print cud.arguments
    #print cud.input_staging
    #print cud.output_staging
    #print cud.cores


    #res_desc = db.get_resource_requirements()
    #pprint (res_desc)


    #confs = db.get_configurations()
    #pprint (confs)
