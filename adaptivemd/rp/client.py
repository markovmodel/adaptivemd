import radical.utils as ru
from database import Database
from resource_manager import ResourceManager
from task_manager import TaskManager
from multiprocessing import Process, Event
from utils import process_resource_description

class Client(object):

    """
    The Client object is instantiated by the AdaptiveMD master in order to invoke components
    on the runtime system (RTS) side. These components then interact with the MongoDB to extract
    task, resource and configuration descriptions. Using these descriptions, RTS specific 
    components are created and executed.
    """

    def __init__(self, dburl, project):

        self._uid = ru.generate_id('client.rp')
        self._logger = ru.get_logger('client.rp')

        self._dburl = dburl
        self._project = project


        # Process related data
        self._proc = None
        self._terminate = None
    
    def start(self):

        self._proc = Process(target=self._runme, args=(,))

        self._terminate = Event()
        self._proc.start()


    def end(self):

        self._terminate.set()


    def _runme(self):

        db = Database(self._dburl, self._project)
        resource_desc = db.get_resource_descriptions()
        processed_resource_desc = process_resource_description(resource_desc)

        rman = ResourceManager(resource_desc = processed_resource_desc, database_url= self._dburl + '/rp')
        rman.submit_resource_request()

        while (db.get_tasks_descriptions() or )