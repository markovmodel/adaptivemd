##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: Jan-Hendrik Prinz
# Contributors:
#
# `adaptiveMD` is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with MDTraj. If not, see <http://www.gnu.org/licenses/>.
##############################################################################
from six import string_types

from .file import (AddPathAction, FileAction, FileTransaction, MakeDir,
                   Copy, Transfer, Link, Move, Remove, Touch)

import os


class ActionParser(object):
    """
    A class that can interprete actions into scheduler understandable commands

    """

    def __init__(self):
        self.parent = None
        self.scheduler = None

    def parse(self, scheduler, action):
        """
        Parse a single action

        Parameters
        ----------
        scheduler : `Scheduler`
            the used scheduler which knows about specifics in the
            parsing process, like, e.g., file paths
        action : `Action` or dict or list of str
            the actual action to be parsed

        Returns
        -------
        list of `Action` or dict or str

        """
        return action

    def __call__(self, scheduler, actions):
        return self._f([self.parse(scheduler, x) for x in actions])

    def __rshift__(self, other):
        return ChainedParser(self, other)

    @staticmethod
    def _f(actions):
        """
        Flatten lists

        Returns
        -------
        list of str or dict or `Action`

        """

        return list(filter(bool, sum([x if isinstance(x, list) else [x] for x in actions], [])))


class DictFilterParser(ActionParser):
    def parse(self, scheduler, action):
        if isinstance(action, dict):
            return action

        return None


class StrFilterParser(ActionParser):
    def parse(self, scheduler, action):
        if isinstance(action, string_types):
            return action

        return None


class ChainedParser(ActionParser):
    """
    Parser that represents the chained application of two parser

    """
    def __init__(self, parent, child):
        super(ChainedParser, self).__init__()
        self.parent = parent
        self.child = child

    def __call__(self, scheduler, actions):
        return self.parent(scheduler, self.child(scheduler, actions))


class StageInParser(ActionParser):
    """
    Special parser that can interpret actions into RP stage-in phase

    """
    def parse(self, scheduler, action):
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


class BashParser(ActionParser):
    def parse(self, scheduler, action):
        if isinstance(action, FileAction):
            sp = action.source.url
            sd = sp.split('://')[0]

            if sd == 'worker':
                sp = sp.split('://')[1]

            if isinstance(action, Transfer):
                if sd == 'file':
                    sp = sp.split('://')[1]

            if isinstance(action, Remove):
                return ['rm %s %s' % (
                    '-r' if action.source.is_folder else '', sp)]
            elif isinstance(action, Touch):
                if action.source.is_folder:
                    return ['mkdir -p %s' % sp]
                else:
                    return ['touch %s' % sp]
            elif isinstance(action, MakeDir):
                if action.source.is_folder:
                    return ['mkdir -p %s' % sp]
            elif isinstance(action, FileTransaction):

                if action.target.is_folder == action.source.is_folder:
                    # file to file and folder to folder
                    rules = stage_rules[action.__class__]
                    if rules['bash_cmd']:
                        tp = action.target.url
                        td = action.target.drive

                        if isinstance(action, Move) and action.source.is_folder:
                            # we cannot just replace an existing folder using `mv`
                            # easiest way is to just move all source files
                            # this will create `mv source/* target/ and mv all files in
                            # source to target and overwrite the targets as we expect

                            return [
                                'mkdir -p %s' % tp,         # create target dir if not exist
                                'mv %s* %s' % (sp, tp),     # move all files
                                'rm -r %s' % sp]            # remove source dir
                        else:
                            if isinstance(action, Transfer):
                                if td == 'file':
                                    tp = tp.split('://')[1]

                            if isinstance(action, Link):
                                # links must not end in `/`
                                if action.target.is_folder:
                                    tp = tp[:-1]
                                    sp = sp[:-1]

                            return ['%s %s %s' % (rules['bash_cmd'], sp, tp)]
        else:
            if isinstance(action, AddPathAction):
                return ['export PATH=%s:$PATH' % action.path]

        return action


class StageParser(ActionParser):
    """
    Parse into possible RP Stage commands for ComputeUnits

    """
    def parse(self, scheduler, action):
        sa_location = scheduler.staging_area_location

        if isinstance(action, FileAction):
            sp = action.source.url

            # useful for RP only
            if sp.startswith(sa_location):
                sp = 'staging://' + sp.split(sa_location)[1]

            sd = sp.split('://')[0]

            if sd == 'worker':
                sp = sp.split('://')[1]

            if isinstance(action, Transfer):
                if sd == 'file':
                    sp = sp.split('://')[1]

            if isinstance(action, FileTransaction):

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

                if action_mode == 'stage':
                    ret = {
                        'source': sp,
                        'target': tp,
                        'action': rules['rp_action']
                    }
                    return ret

        return action


class WorkerParser(ActionParser):
    """
    A parser that can interprete transactions from/to ``file://`` for workers

    This will write the files to the target location instead of a real
    transaction. It requires the file to be stored in the DB using ``load()``

    """
    def parse(self, scheduler, action):
        # all of this is to keep RP compatibility which works with files
        if isinstance(action, FileTransaction):
            source = action.source
            target = action.target

            # create file from
            sp = scheduler.replace_prefix(source.url)
            tp = scheduler.replace_prefix(target.url)

            if source.drive == 'file' and target.drive != 'file':
                if source.has_file:
                    with open(tp, 'w') as f:
                        f.write(source.get_file())

                    return ['# write file `%s` from DB' % tp]
                elif os.path.exists(sp):
                    # in case someone already created the file we need, rename it
                    if sp != tp:
                        return ['ln %s %s' % (sp, tp)]
                else:
                    return ['# Could not write or rename file', action]

            elif target.drive == 'file' and source.drive != 'file':
                return ['ln -s %s %s' % (sp, tp)]

        return action


class PrefixParser(ActionParser):
    """
    Replace all adaptiveMD prefixes

    Usually the last step to convert all file paths

    """
    def parse(self, scheduler, action):
        if isinstance(action, string_types):
            # a bash command, look for prefixes to be parsed
            return [scheduler.replace_prefix(action)]

        return action


# a list of RP implementations and bash commands for each `Action`
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
