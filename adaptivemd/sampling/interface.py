
##############################################################################
# adaptiveMD: A Python Framework to Run Adaptive Molecular Dynamics (MD)
#             Simulations on HPC Resources
# Copyright 2017 FU Berlin and the Authors
#
# Authors: John Ossyra
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

import os
import sys
import traceback

from ..util import get_logger
logger = get_logger(__name__)

from adaptivemd.sampling import functions

user_sampling_functions = os.environ.get("ADMD_SAMPLINGFUNCS", None)


__all__ = ["get_sampling_function", "list_sampling_functions"]


# Error if given non-existing location
# or they don't have an __init__.py there
if user_sampling_functions:
    sys.path.append(user_sampling_functions)
    import user_functions


'''This file provides an interface for using sampling functions
that may be pre-packaged in adaptivemd or written by users.
User-defined functions should take existing examples as a
starting point. The specified sampling function is found and
defined in `get_sampling_function` interface, which handles
the required arguments and passes function-specific ones to
the actual sampling function. This interface provides the
routines that should be replicated
for all sampling functions, currently this is simply converting
them to a runnable form, ie trajectory objects. Sampling
algorithm specifics require at least the basic logic contained here.
'''


def list_sampling_functions():
    # TODO provide list of built-in
    #      and user sampling functions
    pass


def get_sampling_function(name_func, backup_func=None, **sfkwargs): 

    _func = getattr(functions, name_func, None)

    if _func is None:
        _func = getattr(user_functions, name_func, None)

    assert callable(_func)

    if backup_func:
        _backup_func = getattr(functions, backup_func, None) 

        if _backup_func is None:
            _backup_func = getattr(user_functions, backup_func, None) 

        assert callable(_backup_func)

    else:
        _backup_func = None

    logger.info("Retrieved sampling function: {}".format(_func) )
    logger.info("Backup sampling function: {}".format(_backup_func) )

    # Use Sampled Frames to make New Trajectories 
    def sampling_function(project, engine, length, number, *args, **skwargs): 
 
        trajectories = list() 
        skwargs.update(sfkwargs)

        if number == 0:
             return trajectories
 
        if isinstance(length, int): 

            assert(isinstance(number, int)) 
            length = [length] * number 
 
        if isinstance(length, list): 

            if number is None: 
                number = len(length) 
 
            sf = _func 
            sampled_frames = list()

            while not sampled_frames:

                try:
                    sampled_frames = sf(project, number, *args, **skwargs)

                except Exception as e:

                    logger.error("Error: Sampling was unsuccessful due to this error:")
                    logger.error(traceback.print_exc())

                    if (sf == _backup_func) or (_backup_func is None):
                        break

                    else:
                        sf = _backup_func

            logger.info("frames sampled from function: {0}".format(sf))
            logger.info(sampled_frames)

            for i,frame in enumerate(sampled_frames): 
                trajectories.append( 
                    project.new_trajectory(
                    frame, length[i], engine) 
                ) 
 
        return trajectories 
 
    return sampling_function 
