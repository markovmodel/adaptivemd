from __future__ import print_function
import radical.utils as ru
from database import Database
from resource_manager import ResourceManager
from task_manager import TaskManager
from multiprocessing import Process, Event, Manager
from utils import *
from time import sleep
from exceptions import *
import traceback
from pprint import pformat


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

        #self._cb_buffer = CB_Buffer()
        self._cb_manager = Manager()
        self._cb_buffer  = self._cb_manager.list()

        # Process related data
        self._proc = None
        self._cb_proc = None
        self._terminate = None
        self._rmgr = None
        self._tmgr = None

    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------

    def _cb_watcher(self, cb_buffer):
        self._db = Database(self._dburl, self._project)
        # Asynchronous task updates can lead to running
        # state after CU cancellation, any cus in this
        # list will recieve no further state updates
        self._cancelled_cus = list()
        try:
            while not self._terminate.is_set():

                updates = self._cb_check(cb_buffer)

                if not updates:
                    sleep(5)

        except Exception as ex:
            print(traceback.format_exc())
            #pass

        finally:
            if cb_buffer:
                self._logger.warning(
                    'Client process ended before callbacks cleared:\n%s'%pformat(cb_buffer))

    # TODO utilize the 'xxx_many' methods
    #      in pymongo (requires downstream
    #      changes and lumping 'updates')
    def _cb_check(self, cb_buffer):

        updates = False
        while self._cb_buffer:
            updates = True
            cb_dct = self._cb_buffer.pop()
            for uid,operations in cb_dct.items():
                if uid not in self._cancelled_cus:
                    for col,updates in operations.items():
                        while updates:
                            update = updates.pop()
                            if col == 'tasks':
                                self._db.update_task_description_status(uid,update)
                                if 'cancelled' in update:
                                    self._cancelled_cus.append(uid)
                            elif col == 'files':
                                if update == 'create':
                                    self._db.file_created(uid)
                                elif update == 'remove':
                                    self._db.file_removed(uid)

        return updates


    def _get_resource_desc_for_pilot(self, processed_configs, processed_resource_reqs):

        selected_resources = list()

        for resource_reqs in processed_resource_reqs:

            resource_name = resource_reqs['resource']
            matching_configs = get_matching_configurations(configurations=processed_configs, resource_name=resource_name)

            for matched_configs in matching_configs:
                selected_resource = dict()
                selected_resource['resource']       = str(matched_configs['resource'])
                selected_resource['runtime']        = resource_reqs['total_time']
                selected_resource['cores']          = resource_reqs['total_cpus']
                selected_resource['gpus']           = resource_reqs['total_gpus']
                selected_resource['project']        = str(matched_configs['project'])
                selected_resource['queue']          = str(matched_configs['queue'])
                selected_resource['shared_path']    = str(matched_configs.get('shared_path', '$HOME'))

            selected_resources.append(selected_resource)

        # The length of matching_configs is the number of pilots we will launch. Currently, simply return the first 
        # one.

        return selected_resources[0]

    def _runme(self, cb_buffer):

        """
        We run the RP methods in a separate process because although the master process starts these methods,
        we don't want to block the master process.

        NOTE: DO NOT MOVE RP components outside this process. We need to keep them all inside one process since
            they processes will create new copies. Not to be run in separate threads since RP components are not 
            thread-safe.

        """

        try:

            self._db = Database(self._dburl, self._project)
            raw_resource_reqs = self._db.get_resource_requirements()
            processed_resource_reqs = process_resource_requirements(raw_resource_reqs)

            raw_configurations = self._db.get_configurations()
            processed_configurations = process_configurations(raw_configurations)

            resource_desc_for_pilot = self._get_resource_desc_for_pilot(processed_configurations, processed_resource_reqs)

            if len(resource_desc_for_pilot) > 0:

                self._rmgr = ResourceManager(resource_desc = resource_desc_for_pilot, db=self._db)
                self._rmgr.submit_resource_request()

                self._tmgr = TaskManager(session=self._rmgr.session,
                                         db_obj=self._db,
                                         cb_buffer=cb_buffer,
                                         )#scheduler='continuous')#'hombre')#scheduler)

                while not self._terminate.is_set():

                    task_descs = self._db.get_task_descriptions()

                    self._tmgr.cancel_stalled_tasks()

                    if task_descs:
                        cuds = create_cud_from_task_def(task_descs, self._db, resource_desc_for_pilot['shared_path'], self._project)
                        self._tmgr.run_cuds(cuds)

                    else:
                        sleep(3)


            else:
                raise Error(msg="No matching resource found in configuration file. Please check your configuration file and the resource object.")

        except Exception as ex:

            self._logger.error('Client process failed, error: %s'%ex)
            print(traceback.format_exc())
            raise Error(msg=ex)

        finally:

            if self._tmgr:
                #print("CANCELLING TMGR checker")
                self._tmgr.stop_checker()

            if self._rmgr:
                # TODO what to do when _rmgs.pilot is None (ie pilot fails but we get here)?
                self._rmgr.pilot.cancel()
                self._rmgr.session.close(download=True, cleanup=False)


    # ------------------------------------------------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------------------------------------------------

    @property
    def running(self):
        '''
        Check if there is a running RP Client Process
        '''
        if not self._proc:
            return False
        else:
            return self._proc.is_alive()

    def start(self):

        """
        Method exposed to the master process to start all the RP components and processes. This is a non-blocking command.
        """

        try:
            self._proc = Process(target=self._runme, args=(self._cb_buffer,))
            self._terminate = Event()
            self._proc.start()

            self._cb_proc = Process(target=self._cb_watcher, args=(self._cb_buffer,))
            self._cb_proc.start()

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

                self._cb_proc.join()
                self._proc.join()

        except Exception as ex:

            self._logger.error("Error stopping RP process, error: %s"%ex)
            raise Error(msg=ex)

    # ------------------------------------------------------------------------------------------------------------------

