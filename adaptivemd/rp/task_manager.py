import radical.pilot as rp
import radical.utils as ru
import traceback
from utils import create_cud_from_task_def


class TaskManager(object):

    """
    The TaskManager object takes the responsibility of dispatching tasks to a set of resources. In this case,
    the runtime system being used is RADICAL Pilot.


    :arguments:
        :session: The RP session object
        :db_obj: Instance of the Database object as created via .database.py
    """

    def __init__(self, session, db_obj, cb_buffer):

        self._uid           = ru.generate_id('task_manager.rp')
        self._logger        = ru.get_logger('task_manager.rp')
        self._session       = session
        self._db_obj        = db_obj
        self._cb_buffer     = cb_buffer
        self._running_tasks = list()

        self._initialize()

    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------


    def _initialize(self):

        def unit_state_cb(unit, state):

            # O(N) search, could make this an O(log N) search
            # or O(1) if we use hashing, since we assume uid's are unique
            if unit.uid in self._running_tasks:

                # TODO this doesn't get used
                #       - updated to running state when cud is made
                if state == rp.NEW:
                 #   self._db_obj.update_task_description_status(unit.name, 'running')
                    self._cb_buffer.append((unit.name, 'running'))

                elif state in [rp.DONE, rp.UMGR_STAGING_OUTPUT_PENDING]:

                 #   done = self._db_obj.update_task_description_status(unit.name, 'success')

                 #   if done:
                 #       self._db_obj.file_created(unit.name)
                 #       self._db_obj.file_removed(unit.name)
                   # self._cb_buffer['tasks'].append((unit.name,'success'))
                   # self._cb_buffer['files'].append((unit.name,'create'))
                   # self._cb_buffer['files'].append((unit.name,'remove'))
                    self._cb_buffer.append(
                            {unit.name:
                             {'tasks': ['success'],
                              'files': ['create','remove'],
                            }})

                    self._running_tasks.remove(unit.uid)

                elif state == rp.FAILED:
                    self._db_obj.update_task_description_status(unit.name, 'cancelled')
                    self._running_tasks.remove(unit.uid)


        self._umgr = rp.UnitManager(session=self._session)
        pmgr = self._session.get_pilot_managers(pmgr_uids = self._session.list_pilot_managers()[0])
        pilot = pmgr.get_pilots(uids=pmgr.list_pilots()[0])

        self._umgr.add_pilots(pilot)    
        self._umgr.register_callback(unit_state_cb)


    # ------------------------------------------------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------------------------------------------------


    def run_cuds(self, cuds):

        cus = self._umgr.submit_units(cuds)
        self._running_tasks.extend([cu.uid for cu in cus])


    def tasks_done(self):

        return len(self._running_tasks) == 0

    # ------------------------------------------------------------------------------------------------------------------
