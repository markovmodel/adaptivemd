import radical.pilot as rp
import radical.utils as ru
import traceback
from utils import create_cud_from_task_def, create_task_desc_from_cu


class TaskManager(object):


    """
    The TaskManager object takes the responsibility of dispatching tasks to a set of resources. In this case,
    the runtime system being used is RADICAL Pilot.

    """

    def __init__(self, session, db_obj):

        self._uid           = ru.generate_id('task_manager.rp')
        self._logger        = ru.get_logger('task_manager.rp')

        self._session = session
        self._db_obj = db_obj

        self._initialize()

    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------


    def _initialize(self):

        def unit_state_cb(unit, state):

            if state == rp.DONE:
                self._db_obj.update_task(unit.name, 'success')

            elif state == rp.FAILED:
                self._db_obj.update_task(unit.name, 'cancelled')


        self._umgr = rp.UnitManager(session=self._session)
        pmgr = self._session.list_pilot_managers()[0]
        pilot = pmgr.list_pilots()[0]

        self._umgr.add_pilots(pilot)    
        self._umgr.register_callback(unit_state_cb)    


    # ------------------------------------------------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------------------------------------------------


    def run_tasks(self, task_desc):

        cuds = list()
        for task in task_desc:

            cud = create_cud_from_task_def(task)
            cuds.append(cud)

        self._umgr.submit_units(cuds)

    # ------------------------------------------------------------------------------------------------------------------