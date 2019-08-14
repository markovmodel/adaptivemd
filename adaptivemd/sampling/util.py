
import numpy as np

from ..util import get_logger
logger = get_logger(__name__)


def get_model(project, filters=dict()):
    logger.info("Picking last of %s available models" % str(len(project.models)))

    if len(project.models) == 0:
        return None

    models = sorted(project.models,
      reverse=True, key=lambda m: m.__time__)

    # filterkeys: (1 parameter under 1 module) with 1 value
    filters = map(lambda fk,v: (fk.split('.'), v), filters.items())
    for model in models:
        # best thing & somewhat erroneous check is
        # isinstance(model,p.models._set.content_class)
        #assert(isinstance(model, Model))
        if not all([model.data.data.get(mod).get(par) == v for (mod,par),v in filters]):
            continue

        data = model.data
        n_microstates = data['clustering']['k']
        if not n_microstates:
            n_microstates = data['msm']['C'].shape[0]

        c = np.zeros(n_microstates)
        for dtraj in data['clustering']['dtrajs']:
            for f in dtraj:
                c[f] += 1

        logger.info("The selected model analyzed %d trajectories" % len(data['input']['trajectories']))
        return data, c

    else:
        return None


def get_picks(frame_state_list, filelist, npicks, pvec=None, data=None, state_picks=None):

    logger.info("Using probability vector for states q:\n{}".format(pvec))
    nstates = len(frame_state_list)
    if state_picks is None:
        state_picks = np.random.choice(np.arange(nstates), size=npicks, p=pvec)
    elif pvec is not None:
        logger.info("Discarding the given probability vector when state_picks recieved")

    logger.info("Selecting from these states:\n{}".format(state_picks))

    logger.debug("{}".format(filelist))
    trajlist = list()
    picks = list()
    for state in state_picks:
        logger.debug("Looking at state: ".format(state))
        logger.debug("{}".format(frame_state_list[state]))
        pick = frame_state_list[state][
                # FIXME should this be len()-1?
                np.random.randint(0, len(frame_state_list[state]))
        ]

        picks.append(pick)
        # FIXME the goal with this seems to have been use of a subsample of data
        if data:
            #state_from_dtrajs = data['clustering']['dtrajs'][pick[0]][dfti(data, pick[1])]
            logger.debug("dtraj {}".format(data['clustering']['dtrajs'][pick[0]]))

        logger.info("For state {0}, picked this frame: {1}  {2} from traj  {3}  --  {4}".format(state, picks[-1], filelist[pick[0]][pick[1]], filelist[pick[0]], pick))

    [trajlist.append(filelist[pick[0]][pick[1]]) for pick in picks]

    return trajlist

def list_microstate_frames(data):
    '''
    This function returns a dict with items that contain the frames
    belonging to each microstate. While the trajectories analyzed for
    the data might have a more frequent stride than the all-atoms
    trajectory, only the all-atoms trajectory can be used for sampling
    since the restart frame must contain the whole system. So the
    returned lists only contain frames that are saved in the all-atoms
    trajectory data.

    keys :: int
    microstate index

    values :: list
    frames belonging to this microstate

    '''
    # not a good method to get n_states
    # populated clusters in
    # data['msm']['C'] may be less than k
    #n_states = data['clustering']['k']
    n_states = len(data['msm']['C'])
    modeller = data['input']['modeller']
    outtype = modeller.outtype
    # the stride of the analyzed trajectories
    used_stride = modeller.engine.types[outtype].stride
    # all stride for full trajectories
    full_strides = modeller.engine.full_strides
    frame_state_list = {n: [] for n in range(n_states)}
    for nn, dt in enumerate(data['clustering']['dtrajs']):
        for mm, state in enumerate(dt):
            # if there is a full traj with existing frame, use it
            if any([(mm * used_stride) % _stride == 0 for _stride in full_strides]):
                frame_state_list[state].append((nn, mm * used_stride))
                #print("Appended frame: TJidx {0} Fidx {1} State {2} to framestatelist".format(
                #        nn, mm, state))
    return frame_state_list
