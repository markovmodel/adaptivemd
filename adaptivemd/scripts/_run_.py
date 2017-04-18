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


"""
Python script for the RPC Python call for Adaptive MD

This executes a function remotely and expects an `input.json` file to contain
a reference to the function and module as well as arguments and keyword arguments
"""


import importlib
from adaptivemd.mongodb import ObjectJSON
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

simplifier = ObjectJSON()

with open('input.json', 'r') as f:
    data = simplifier.from_json(f.read())

parts = data['function'].split('.')

fnc = importlib.import_module('.'.join(parts[:-1]))
fnc = getattr(fnc, parts[-1])

result = fnc(**data['kwargs'])

with open('output.json', 'w') as f:
    f.write(simplifier.to_json(result))
