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


# Decide what to do with the current model

from analysis import DoAnalysis
from mongodb import StorableMixin


class Brain(StorableMixin):
    def __init__(self, engine, analyzer):
        super(Brain, self).__init__()
        self.engine = engine
        self.analyzer = analyzer

    def execute(self, project):
        # add events
        map(project.add_event, self.get_events(project))

        # submit initial tasks
        project.submit(self.initial_tasks(project))

    def initial_tasks(self, project):
        return project.new_trajectory(project.engine['pdb'], 10, number=2)

    def get_events(self, project):
        event_analysis = DoAnalysis(
            when=project.on_ntraj(range(5, 100, 5)),
            modeller=project['modeller']
        )

        return [
            event_analysis
        ]
