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

    def __init__(self, session, db_obj, cb_buffer, scheduler):

        self._uid           = ru.generate_id('task_manager.rp')
        self._logger        = ru.get_logger('task_manager.rp')
        self._session       = session
        self._scheduler     = scheduler
        # NOTE if the cu.uid update is moved then the db obj can be
        #      entirely removed from the task manager since it
        #      acts throught the buffer (ie move this update to buffer)
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

                if state == rp.AGENT_EXECUTING_PENDING:
                    self._cb_buffer.append({unit.name: {'tasks': ['running']}})

                elif state in [rp.DONE, rp.UMGR_STAGING_OUTPUT_PENDING]:

                    self._cb_buffer.append(
                            {unit.name:
                             {'tasks': ['success'],
                              'files': ['create','remove'],
                            }})

                    self._running_tasks.remove(unit.uid)

                elif state == rp.FAILED:

                    self._cb_buffer.append({unit.name: {'tasks': ['cancelled']}})
                    self._running_tasks.remove(unit.uid)


        self._umgr = rp.UnitManager(session=self._session, scheduler=self._scheduler)
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

        [self._db_obj.db[self._db_obj.tasks_collection].update_one(
                                    {"_id": cu.name},
                                    {"$set": {"cuid": cu.uid}}
                                   )
        for cu in cus]

    def tasks_done(self):

        return len(self._running_tasks) == 0

    # ------------------------------------------------------------------------------------------------------------------
