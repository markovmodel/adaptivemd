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

    def __init__(self, session, db_obj):

        self._uid           = ru.generate_id('task_manager.rp')
        self._logger        = ru.get_logger('task_manager.rp')

        self._session = session
        self._db_obj = db_obj

        self._running_tasks = list()

        self._initialize()

    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------


    def _initialize(self):

        def unit_state_cb(unit, state):

            if state == rp.DONE:
                self._db_obj.update_task(unit.name, 'success')
                self._running_tasks.remove(unit.uid)

            elif state == rp.FAILED:
                self._db_obj.update_task(unit.name, 'cancelled')
                self._running_tasks.remove(unit.uid)


        self._umgr = rp.UnitManager(session=self._session)
        pmgr = self._session.list_pilot_managers()[0]
        pilot = pmgr.list_pilots()[0]

        self._umgr.add_pilots(pilot)    
        self._umgr.register_callback(unit_state_cb)    


    # ------------------------------------------------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------------------------------------------------


    def run_cuds(self, task_desc):

        cuds = list()
        for task in task_desc:

            cud = create_cud_from_task_def(task)
            cuds.append(cud)

        cus = self._umgr.submit_units(cuds)
        self._running_tasks.extend([cu.uid for cu in cus])


    def tasks_done(self):

        return len(self._running_tasks) == 0

    # ------------------------------------------------------------------------------------------------------------------