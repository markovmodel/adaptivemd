from database import Database
from pprint import pprint
from utils import create_cud_from_task_def

if __name__ == '__main__':

    db = Database(db_url='mongodb://user:user@two.radical-project.org:32769/', project='storage-rp_testing')
    
    #create_cud_from_task_def(db.get_tasks_definitions()[0])
    task_desc = db.get_tasks_descriptions()

    pprint(task_desc[0])
    #create_cud_from_task_def(task_desc[0])