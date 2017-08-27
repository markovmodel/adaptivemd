from database import Database
from pprint import pprint
from utils import create_cud_from_task_def

if __name__ == '__main__':

    db = Database(mongo_url='mongodb://user:user@two.radical-project.org:32769/', project='rp_testing_3')
    
    #create_cud_from_task_def(db.get_tasks_definitions()[0])
    task_desc = db.get_task_descriptions()

    #pprint(task_desc[0])
    cud = create_cud_from_task_def(task_desc[0], '$HOME/vivek')
    print cud.name
    print cud.executable
    print cud.arguments
    print cud.input_staging
    print cud.output_staging
    print cud.cores


    res_desc = db.get_resource_requirements()
    #pprint (res_desc)


    confs = db.get_configurations()
    #pprint (confs)
