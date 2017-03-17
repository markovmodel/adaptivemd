from file import Remove, FileTransaction, Copy, Transfer, Link, Move, \
    AddPathAction, FileAction, Touch


def parse_action_stage_in(scheduler, action):
    if isinstance(action, FileTransaction):
        source = action.source
        target = action.target

        sp = source.url
        tp = target.url

        ret = {
            'source': sp,
            'target': tp,
            'action': 'Transfer'  # rp.TRANSFER
        }
        return ret

    return action


def parse_action(scheduler, action, bash_only=False):
    """
    Interprete an action to be run using RP

    Parameters
    ----------
    scheduler : `Scheduler`
        the `Scheduler` the action should be prepared for
    action : `Action`
        the `Action` to be parsed
    bash_only : bool
        if True this will return only bash commands and no RP staging dicts

    Returns
    -------
    list or dict
        A list of bash commands or a dict the represents a staging command in RP

    """
    sa_location = scheduler.staging_area_location

    if isinstance(action, FileAction):
        sp = action.source.url

        if sp.startswith(sa_location):
            sp = 'staging://' + sp.split(sa_location)[1]

        sd = sp.split('://')[0]

        if sd == 'worker':
            sp = sp.split('://')[1]

        if isinstance(action, Transfer):
            if sd == 'file':
                sp = sp.split('://')[1]

        if isinstance(action, Remove):
            sp = scheduler.replace_prefix(sp)

            return ['rm %s %s' % (
                '-r' if action.source.is_folder else '', sp)]
        elif isinstance(action, Touch):
            sp = scheduler.replace_prefix(sp)

            return ['touch %s' % sp]
        elif isinstance(action, FileTransaction):

            tp = action.target.url
            td = action.target.drive
            if td == 'worker':
                tp = tp.split('://')[1]

            if isinstance(action, Transfer):
                if td == 'file':
                    tp = tp.split('://')[1]

            rules = stage_rules[action.__class__]
            signature = (sd, td)

            action_models = rules['folder' if action.source.is_folder else 'file']
            action_mode = action_models.get(signature)
            if bash_only:
                # make sure there is a bash equivalent otherwise pass
                if rules['bash_cmd']:
                    action_mode = 'bash'
                else:
                    return action

            if action_mode == 'stage':
                ret = {
                    'source': sp,
                    'target': tp,
                    'action': rules['rp_action']
                }
                return ret
            elif action_mode == 'bash':
                sp = scheduler.replace_prefix(sp)
                tp = scheduler.replace_prefix(tp)

                s = ['%s %s %s' % (rules['bash_cmd'], sp, tp)]
                return s

    else:
        if isinstance(action, AddPathAction):
            return ['export PATH=%s:$PATH' % action.path]

    return action


def parse_transfer_worker(scheduler, action):
    """
    Parse a file transaction transfer for workers

    Parameters
    ----------
    scheduler
    action

    Returns
    -------

    """

    if isinstance(action, FileTransaction):
        source = action.source
        target = action.target
        if (source.drive == 'file' and target.drive != 'file') or (target.drive == 'file' and source.drive != 'file'):
            sp = scheduler.replace_prefix(source.url)
            tp = scheduler.replace_prefix(target.url)

            ret = []

            print source, source.has_file

            if source.has_file:
                with open(sp, 'w') as f:
                    f.write(source.get_file())
                    print 'WRITING file `%s`' % sp

                ret += ['# write file `%s` from DB' % sp]

            ret += ['mv %s %s' % (sp, tp)]

            return ret

    return action


def apply_reducer(reducer, scheduler, actions, *args, **kwargs):
    return [reducer(scheduler, action, *args, **kwargs) for action in actions]


def filter_dict(actions):
    return filter(bool, filter(lambda x: isinstance(x, dict), actions))


def filter_str(actions):
    return \
        sum([x if isinstance(x, list) else [x] for x in
            filter(bool, filter(
                lambda y: isinstance(y, (list, str)), actions))], [])


stage_rules = {
    Copy: {
        'file': {
            ('staging', 'worker'): 'stage',
            ('worker', 'staging'): 'stage',
            ('sandbox', 'worker'): 'bash',
            ('shared', 'worker'): 'bash',
            ('worker', 'shared'): 'bash',
            ('shared', 'shared'): 'bash',
            ('shared', 'staging'): 'bash',
            ('staging', 'shared'): 'bash'
        },
        'folder': {
            ('staging', 'worker'): 'bash',
            ('worker', 'staging'): 'bash',
            ('sandbox', 'worker'): 'bash',
            ('shared', 'worker'): 'bash',
            ('worker', 'shared'): 'bash',
            ('shared', 'shared'): 'bash',
            ('shared', 'staging'): 'bash',
            ('staging', 'shared'): 'bash'
        },
        'bash_cmd': 'cp',
        'rp_action': 'Copy'  # rp.COPY
    },
    Transfer: {
        'file': {
            ('file', 'worker'): 'stage',
            ('file', 'staging'): 'stage',
            ('staging', 'worker'): 'stage',
            ('staging', 'file'): 'stage',
            ('worker', 'staging'): 'stage',
            ('worker', 'file'): 'stage'
        },
        'folder': {
        },
        'bash_cmd': None,
        'rp_action': 'Transfer'  # rp.TRANSFER
    },
    Move: {
        'file': {
            ('staging', 'worker'): 'stage',
            ('worker', 'staging'): 'stage',
            ('sandbox', 'worker'): 'bash',
            ('shared', 'worker'): 'bash',
            ('worker', 'shared'): 'bash',
            ('shared', 'shared'): 'bash',
            ('shared', 'staging'): 'bash',
            ('staging', 'shared'): 'bash'
        },
        'folder': {
            ('staging', 'worker'): 'bash',
            ('worker', 'staging'): 'bash',
            ('sandbox', 'worker'): 'bash',
            ('shared', 'worker'): 'bash',
            ('worker', 'shared'): 'bash',
            ('shared', 'shared'): 'bash',
            ('shared', 'staging'): 'bash',
            ('staging', 'shared'): 'bash'
        },
        'bash_cmd': 'mv',
        'rp_action': 'Move'  # rp.MOVE
    },
    Link: {
        'file': {
            ('staging', 'worker'): 'stage',
            ('sandbox', 'worker'): 'bash',
            ('shared', 'worker'): 'bash'
        },
        'folder': {
            ('staging', 'worker'): 'bash',
            ('sandbox', 'worker'): 'bash',
            ('shared', 'worker'): 'bash'
        },
        'bash_cmd': 'ln -s',
        'rp_action': 'Link'  # rp.LINK
    }
}
