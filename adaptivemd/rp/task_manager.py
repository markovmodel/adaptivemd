import radical.pilot as rp
import radical.utils as ru
import traceback

class TaskManager(object):

    def __init__(self, session):

        self._uid           = ru.generate_id('radical.entk.task_manager')
        self._logger        = ru.get_logger('radical.entk.task_manager')

        self._session = session


    def run_tasks(self, task_desc):

        for task in task_desc:

            
            
