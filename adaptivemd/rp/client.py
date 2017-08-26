import radical.utils as ru
from database import Database
from resource_manager import ResourceManager
from task_manager import TaskManager
from multiprocessing import Process, Event
from utils import process_resource_description, create_cud_from_task_def
from time import sleep
from exceptions import *

class Client(object):

    """
    The Client object is instantiated by the AdaptiveMD master in order to invoke components
    on the runtime system (RTS) side. These components then interact with the MongoDB to extract
    task, resource and configuration descriptions. Using these descriptions, RTS specific 
    components are created and executed.

    :arguments:
        :dburl: MongoDB URL to be used for RADICAL Pilot
        :project: Store name to be used on MongoDB. This is the store where all the configurations, resources and task 
                    descriptions are present.
    """

    def __init__(self, dburl, project):

        self._uid = ru.generate_id('client.rp')
        self._logger = ru.get_logger('client.rp')

        self._dburl = dburl
        self._project = project


        # Process related data
        self._proc = None
        self._terminate = None


    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------

    def _runme(self):

        """
        We run the RP methods in a separate process because although the master process starts these methods,
        we don't want to block the master process.

        NOTE: DO NOT MOVE RP components outside this process. We need to keep them all inside one process since
            they processes will create new copies. Not to be run in separate threads since RP components are not 
            thread-safe.

        """


        try:

            self._db = Database(self._dburl, self._project)
            raw_resource_desc = self._db.get_resource_descriptions()
            processed_resource_desc = process_resource_description(raw_resource_desc)

            self._rmgr = ResourceManager(resource_desc = processed_resource_desc, database_url= self._dburl + '/rp')
            self._rmgr.submit_resource_request()

            self._tmgr = TaskManager(session=self._rmgr.session, db_obj=self._db)

            while self._terminate.is_set():

                task_desc = self._db.get_tasks_descriptions()

                if task_desc:
                    cuds = create_cud_from_task_def(task_desc)
                    self._tmgr.run_cuds(cuds)

                else:
                    sleep(3)

        except Exception as ex:

            self._logger.error('Client process failed, error: %s'%ex)
            raise Error(msg=ex)

        finally:

            self._rmgr.pilot.cancel()
            self._rmgr.session.close(cleanup=False)



    # ------------------------------------------------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------------------------------------------------

    def start(self):

        """
        Method exposed to the master process to start all the RP components and processes. This is a non-blocking command.
        """

        try:
            self._proc = Process(target=self._runme, args=(,))
            self._terminate = Event()
            self._proc.start()

        except Exception as ex:

            self._logger.error("Error starting RP process, error: %s"%ex)
            self.end()
            raise Error(msg=ex)


    def stop(self):

        """
        Method exposed to the master process to end all the RP components and processes. This is a blocking command.
        """

        try:

            if self._proc.is_alive():

                if not self._terminate.is_set():
                    self._terminate.set()

                self._proc.join()

        except Exception as ex:

            self._logger.error("Error stopping RP process, error: %s"%ex)
            raise Error(msg=ex)

    # ------------------------------------------------------------------------------------------------------------------