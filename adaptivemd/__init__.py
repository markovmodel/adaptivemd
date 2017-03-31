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

# part of the code below was taken from `openpathsampling` see
# <http://www.openpathsampling.org> or
# <http://github.com/openpathsampling/openpathsampling
# for details and license


from brain import Brain
from event import StopEvent, Event, TasksFinished, FunctionalEvent, event
from condition import Condition, Now, Never
from file import File, Copy, Link, Move, Remove, Transfer, Directory, AddPathAction, Location, \
    JSONFile
from bundle import Bundle, SortedBundle, ViewBundle
from resource import AllegroCluster, LocalResource
from task import Task, PythonTask, DummyTask
from project import Project
from scheduler import Scheduler
from model import Model
from generator import TaskGenerator
from worker import WorkerScheduler, Worker
from logentry import LogEntry
from reducer import ActionParser, BashParser, ChainedParser, DictFilterParser, \
    PrefixParser, StageParser, StrFilterParser, StageInParser

from engine import Engine, Trajectory, Frame, \
    TrajectoryGenerationTask, TrajectoryExtensionTask
from analysis import Analysis, DoAnalysis

# specific generators that should be available to the general user
# this simplifies loading objects. Otherwise you need to import them
# manually before they can be loaded

from engine.openmm import OpenMMEngine
from analysis.pyemma import PyEMMAAnalysis

import util

from util import DT
