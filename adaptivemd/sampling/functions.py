
import numpy as np

from ..util import get_logger
logger = get_logger(__name__)

from .util import get_picks, get_model, list_microstate_frames


def random_sampling_trajectories(project, number=1, **kwargs):
    '''
    Randomly sample frames from the body of trajectory data.
    Low energy regions will be heavily sampled from simulations
    distributed as a Gibbs Ensemble, as simulation time is
    presumably Boltzmann-distributed to these regions.
    '''

    trajlist = list()

    if len(project.trajectories) > 0:
        logger.info("Random selection of new frames from trajectory data")
        [trajlist.append(project.trajectories.pick().pick()) for _ in range(number)]

    return trajlist


def random_sampling_microstates(project, number=1, **kwargs):
    '''Randomly sample frames across microstates
    from the clustered trajectory data. This should result in a
    roughly uniform exploration of the already visited state space.
    '''

    trajlist = list()
    data, c = get_model(project)

    filelist = data['input']['trajectories']
    frame_state_list = list_microstate_frames(data)
    states = frame_state_list.keys()
    # remove states that do not have at least one frame
    # can't iterate over states while also changing states
    # so using len(c), states is same range
    for state in states:
        if len(frame_state_list[state]) == 0:
            logger.info("This state was empty: {}".format(state))
            states.remove(state)

    nstates = len(states)
    w = 1./nstates
    q = [w if state in states else 0 for state in frame_state_list]
    trajlist = get_picks(frame_state_list, filelist, number, pvec=q, data=None)

    return trajlist


def uniform_sampling_microstates(project, number=1, **kwargs):
    '''Select a state from each microstate
    until the specified number of restart states have been sampled.
    If `number` is not a multiple of the number of states, the
    states cannot be uniformly sampled.
    '''
    trajlist = list()
    data, c = get_model(project)

    filelist = data['input']['trajectories']
    frame_state_list = list_microstate_frames(data)
    states = frame_state_list.keys()
    # remove states that do not have at least one frame
    # can't iterate over states while also changing states
    # so using len(c), states is same range
    for state in states:
        if len(frame_state_list[state]) == 0:
            states.remove(state)

    logger.info("Uniformly sampling {0} frames across {1} microstates".format(number, c.shape[0]))
    _states = iter(states)
    while len(trajlist) < number:
        try:
            state = next(_states)
            pick = frame_state_list[state][np.random.randint(0,
                    # TODO this should be done by the picks/get_picks functions
                    len(frame_state_list[state]))]
            trajlist.append(filelist[pick[0]][pick[1]])
            state_from_dtrajs = data['clustering']['dtrajs'][pick[0]][dfti(data, pick[1])]
            logger.info("For state {0}, picked this frame: {1}  {2}   --  {3}".format(
                    state, state_from_dtrajs, trajlist[-1], pick
            ))
        except StopIteration:
            _states = iter(states)

    return trajlist


def explore_microstates(project, number=1, **kwargs):
    '''Inverse-count sampling of microstates
    '''

    d = get_model(project)
    if not d:
        return None
    data, c = d
    filelist = data['input']['trajectories']
    # TODO verify axis 0 is the columns
    # TODO dont' do above todo, but ...
    #      do ceiling(average(rowcount, colcount)) as weight
    #q = 1/np.sum(c, axis=1)
    q = 1/c
    trajlist = list()

    frame_state_list = list_microstate_frames(data)
    # remove states that do not have at least one frame
    for k in range(len(q)):
        if len(frame_state_list[k]) == 0:
            q[k] = 0.0
    # and normalize the remaining ones
    q /= np.sum(q)
    #trajlist = get_picks(frame_state_list, filelist, number, pvec=q, data=data)
    trajlist = get_picks(frame_state_list, filelist, number, pvec=q, data=None)

    logger.info("Trajectory picks list:\n{}".format(trajlist))
    return trajlist


def explore_macrostates(project, n_frames=1, num_macrostates = 30, reversible=True, **kwargs):
    '''Inverse-count sampling of macrostates
    '''

    model_parameters = {'tica':['lagtime','stride'],'clustering':['k'],'msm':['lagtime']}

    def select_restart_state(values, select_type, microstates, nparallel=1, parameters=None):
        if select_type == 'sto_inv_linear':
            if not isinstance(values, np.ndarray):
                values = np.array(values)
            inv_values = 1.0 / values
            p = inv_values / np.sum(inv_values)
            logger.info("Values: {}".format(values))
            logger.info("Problt: {}".format(p))
        else:
            logger.info("Unsupported selection type")
            return

        return np.random.choice(microstates, p = p, size=nparallel)

    def MinMaxScale(X, min=-1, max=1):
        X_std = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0))
        X_scaled = X_std * (max - min) + min
        return X_scaled

    # TODO   MOVE TO analysis task: adaptivemd.analysis.pyemma._remote
    import time
    import pyemma
    import msmtools

    pyemma.config.show_progress_bars = False
    starttime = time.time()
    logger.info("USING EXPLORE MACROSTATES STRATEGY")
    logger.info("Starting Timer at: {}".format(starttime))
    model_filters  = {}

    for mod,pars in model_parameters.items():
        for par in pars:
            key = '.'.join([mod,par])
            val = kwargs.get(key)
            if val is not None:
                model_filters[key] = val

    try:
        data, _c  = get_model(project, model_filters)

    except TypeError:
        # No matching models
        return [] # No trajs made
        #raise    # Backup method may be used

    c         = data['msm']['C']
    counts    = np.array(np.sum(c, axis=1), dtype=int)
    array_ok  = msmtools.estimation.largest_connected_set(c)
    num_macrostates = min(num_macrostates, array_ok.shape[0]/3)
    connected = msmtools.estimation.is_connected(c[array_ok,:][:,array_ok])
    disconnected_microstates = [i for i in range(c.shape[0]) if i not in array_ok]
    logger.info("Coarse Graining to {} macrostates".format(num_macrostates))
    logger.info("c.shape: {}".format(c.shape))
    #logger.info("array_ok: {}".format(array_ok))
    logger.info("Disconnected Microstates: {}".format(disconnected_microstates))
    logger.debug("array_ok.__len__: {}".format(len(array_ok)))
    logger.info("Connected Dataset: {0} {1}".format(connected, len(array_ok)))
    p = msmtools.estimation.transition_matrix(c[array_ok,:][:,array_ok], reversible=reversible)
    logger.info("Making MSM from transition matrix")
    current_MSM_obj    = pyemma.msm.markov_model(p)
    current_timescales = current_MSM_obj.timescales()
    logger.debug("Timescales from microstate MSM: {}".format(current_timescales))
    #num_macrostates = max(cut.shape[0],1)
    #
    #   PCCA  Macrostates
    #
    logger.info("Making CG MSM")
    current_MSM_obj.pcca(num_macrostates)
    macrostate_assignments = { k:v for k,v in enumerate(current_MSM_obj.metastable_sets) }
    macrostate_assignment_of_visited_microstates = current_MSM_obj.metastable_assignments
    corrected = np.zeros(c.shape[0])
    corrected[array_ok] = macrostate_assignment_of_visited_microstates

    for n,i in enumerate(disconnected_microstates):
        corrected[i]=n+num_macrostates

    logger.info("Macrostates including unassigned (index over num_macrostates): {}".format(corrected))
    #del#counts=np.sum(c,axis=1)
    #[array_ok,:][:,array_ok]
    logger.debug("Macrostate summer: {}".format([counts[corrected == macrostate_label] for macrostate_label in range(num_macrostates+len(disconnected_microstates))]))
    macrostate_counts   = np.array([np.sum(counts[corrected == macrostate_label])      for macrostate_label in range(num_macrostates+len(disconnected_microstates))])
    # Set count to zero in disconnected 'macrostates'<-->microstates
    #macrostate_counts[num_macrostates:] = 0
    logger.info("Macrostate Assignments: {}".format('\n'.join(["{0}: {1}".format(k,v)  for k,v in macrostate_assignments.items()])))
    logger.info("Microstate Counts: {}".format(counts))
    logger.info("Macrostate Counts: {}".format(macrostate_counts))
    # TODO why not just use macrostate_counts array in the arange?
    ma_counted = macrostate_counts[macrostate_counts > 0]

    selected_macrostate = select_restart_state(
        ma_counted + (
        np.sum(ma_counted)/float(ma_counted.shape[0]))**0.5,
        'sto_inv_linear',
        np.arange(num_macrostates+len(
          disconnected_microstates))[
          macrostate_counts > 0],
        nparallel=n_frames)

    logger.info("Selected Macrostates: {}".format(selected_macrostate))
    restart_state = np.empty((0))

    for i in range(n_frames):
        selected_macrostate_mask      = (corrected == selected_macrostate[i])
        logger.debug("Macrostate Selection Mask: ({0})\n{1}".format(selected_macrostate[i], selected_macrostate_mask))
        #counts_in_selected_macrostate = counts[selected_macrostate_mask]
        counts_in_selected_macrostate = np.ones(len(counts))[selected_macrostate_mask]
        add_microstate                = select_restart_state(counts_in_selected_macrostate, 'sto_inv_linear', np.arange(c.shape[0])[selected_macrostate_mask], nparallel=1)
        logger.info("Selected Macrostate, microstate: {0}, {1}".format(selected_macrostate[i], add_microstate))
        restart_state                 = np.append(restart_state, add_microstate)

    state_picks  = restart_state.astype('int')
    frame_state_list = list_microstate_frames(data)
    filelist = data['input']['trajectories']
    trajlist = get_picks(frame_state_list, filelist, n_frames, data=None, state_picks=state_picks)
    #trajlist = get_picks(frame_state_list, filelist, n_frames, data=data, state_picks=state_picks)
    stoptime = time.time()
    logger.info("Stopping Timer at: {}".format(stoptime))
    logger.info("Explore Macrostates duration: {}".format(stoptime - starttime))

    return trajlist

