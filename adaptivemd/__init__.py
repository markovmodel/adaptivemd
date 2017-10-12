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
from __future__ import absolute_import

#from .brain import Brain
# from event import StopEvent, Event, TasksFinished
from .plan import ExecutionPlan
# from condition import Condition, Now, Never
from .file import (File, Directory, Location, JSONFile, MakeDir, Copy,
                   Transfer, Link, Move, Remove, Action, AddPathAction, FileAction,
                   FileTransaction, Touch)
from .bundle import (Bundle, SortedBundle, ViewBundle, AndBundle,
                     BaseBundle, BundleDelegator, FunctionDelegator, LogicBundle,
                     OrBundle, StoredBundle)
#from .resource import LocalResource
from .configuration import Configuration
from .task import Task, PythonTask, DummyTask
from .project import Project
from .scheduler import Scheduler
from .model import Model
from .generator import TaskGenerator
from .worker import WorkerScheduler, Worker
from .logentry import LogEntry
from .reducer import (ActionParser, BashParser, ChainedParser,
                      DictFilterParser, PrefixParser, StageParser, StrFilterParser,
                      StageInParser)

from .engine import (Engine, Trajectory, Frame,
                     TrajectoryGenerationTask, TrajectoryExtensionTask)
from .analysis import Analysis, DoAnalysis

# specific generators that should be available to the general user
# this simplifies loading objects. Otherwise you need to import them
# manually before they can be loaded

from .engine.openmm import OpenMMEngine
from .analysis.pyemma import PyEMMAAnalysis

from . import util

from .util import DT

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

#from .rp.client import Client
