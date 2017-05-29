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

from .mongodb import StorableMixin


class Model(StorableMixin):
    """
    A wrapper to hold model data

    Examples
    --------
    >>> m = Model({'msm' : [[0.9, 0.1], [0.1, 0.9]]})
    >>> print(m.msm)
    [[0.9, 0.1], [0.1, 0.9]]
    >>> print(m['msm'])
    [[0.9, 0.1], [0.1, 0.9]]


    Attributes
    ----------
    data : dict of str : anything
        the data of the model
    """
    def __init__(self, data):
        super(Model, self).__init__()
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __getattr__(self, item):
        if item in self.data:
            return self.data[item]