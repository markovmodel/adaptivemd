import radical.pilot as rp
import radical.utils as ru
import traceback
from utils import create_cud_from_task_def
import time

from database import Database

#from pprint import pformat

from multiprocessing import Process, Manager, Event


class TaskManager(object):

    """
    The TaskManager object takes the responsibility of dispatching tasks to a set of resources. In this case,
    the runtime system being used is RADICAL Pilot.


    :arguments:
        :session: The RP session object
        :db_obj: Instance of the Database object as created via .database.py
    """

    def __init__(self, session, db_obj, cb_buffer, scheduler=None):

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

        # This dict will take each batch of tasks
        # and check that they are running, or else
        # cancel them after a waiting period
        self._running_mgr   = Manager()
        #
        # structure of this dict: 
        #         batch info              need2check             need2kill
        #    { (starttime, waittime) : [ [cu.uid, cu.uid, ... ], [cu.uid, cu.uid, ... ] ],
        #      () : [ ... ],
        #        ...
        #    }
        #
        self._running_checklist = self._running_mgr.dict()

        self._initialize()

    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------


    def _initialize(self):

        def unit_state_cb(unit, state):

            #print "CALLBACK state: ", unit.uid, state
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

                elif state == rp.CANCELED:

                    self._cb_buffer.append({unit.name: {'tasks': ['cancelled']}})
                    self._running_tasks.remove(unit.uid)


        kwargs_umgr = {"session": self._session}
        if self._scheduler:
            kwargs_umgr["scheduler"] = self._scheduler

        self._umgr  = rp.UnitManager(**kwargs_umgr)
        pmgr = self._session.get_pilot_managers(pmgr_uids = self._session.list_pilot_managers()[0])
        pilot = pmgr.get_pilots(uids=pmgr.list_pilots()[0])

        self._umgr.add_pilots(pilot)    
        self._umgr.register_callback(unit_state_cb)

        self._running_check_proc = Process(
                target=self._running_checker,
                args=(self._running_checklist,self._db_obj.url,self._db_obj.project))
        self._terminate = Event()
        self._running_check_proc.start()


    def _running_checker(self, checklist, dburl, projectname):
        self._db_obj = Database(dburl, projectname)
        task_col = self._db_obj.db[self._db_obj.tasks_collection]
        while not self._terminate.is_set():
            # Get a batch of cu's to check
            for j,((starttime,waittime),(cuids,kills)) in enumerate(checklist.items()):
                if cuids:
                    for i,cuid in enumerate(cuids):
                        entry = task_col.find_one({"cuid": cuid}, projection=["state"])
                        if entry:
                            if entry["state"] in {"created", "pending"} and time.time() - starttime > waittime:
                                #print "Triggering kill for this one: ", cuid, i
                                #print "BEFORE modification: ", cuids, kills
                                kills.append(cuids.pop(i))
                                #print "We'd remove this one {} here".format(cuids[i])
                                #print "AFTER  modification: ", cuids, kills
                                # Its been too long since the batch was scheduled
                                #self._db_obj.update_task_description_status(entry["_id"], 'cancelled')
                            elif entry["state"] in {"running","fail","success","cancelled"}:
                                # Remove units if they are running, finished, or cancelled
                                #print "GONNA REMOVE cuid: ", cuid
                                cuids.remove(cuid)

                    checklist[(starttime,waittime)] = [cuids,kills]

                elif not kills:
                    # All cu's checked from this batch and
                    # kills have been handled
                    #checklist.remove( (starttime,waittime) )
                    del checklist[(starttime,waittime)]

                #print "OUTSIDE  modification: ||| {0} || {1} |||".format(cuids, kills)

            time.sleep(3)


    # ------------------------------------------------------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------------------------------------------------------


    def cancel_stalled_tasks(self):
        #print "I would cancel these tasks: "
        for times, (cuids,kills) in self._running_checklist.items():
            #print "GONNA KILL THESE", kills
            if kills:
                self._running_checklist[times] = [cuids, [] ]
                self._umgr.cancel_units(kills)


    def stop_checker(self):
        #print "STOPPING running checker"
        self._terminate.set()
        self._running_check_proc.join()


    def run_cuds(self, cuds):

        cus = self._umgr.submit_units(cuds)
        self._running_tasks.extend([cu.uid for cu in cus])

        [self._db_obj.db[self._db_obj.tasks_collection].update_one(
                                    {"_id": cu.name},
                                    {"$set": {"cuid": cu.uid}}
                                   )
        for cu in cus]

        # if after the wait time there are units not running
        # then these will be canceled. They should schedule
        # and start faster than 10 tasks / second.
        self._running_checklist[
                (time.time(),
                30 + len(cuds) / (8.))] = [[cu.uid for cu in cus], [] ]

        #print "AFTER adding newlist: ", pformat(self._running_checklist)


    def tasks_done(self):

        return len(self._running_tasks) == 0

    # ------------------------------------------------------------------------------------------------------------------
