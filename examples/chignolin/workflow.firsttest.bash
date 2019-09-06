#!/bin/bash

# Folder containing PDB and OpenMM Simulation XML Files
#  - in '$ADMD_ADAPTIVEMD/examples/files/' or user-specified path in "$ADMD_MDSYSTEMS"
SYS="chignolin"

# Walltime for LRMS job
MINS="15"

# DB Setup: fields separated by colon- "path[:port[:'persist']]"
#  1. relative or absolute path to DB parent folder
#  2. optional (somewhat random) DB port for client-side database
#      - uses MongoDB default 27017 if not given
#  3. optional flag to use a persistent, client-side database instance

# Valid DB Setup Arguments
#DBSETUP="mongo"
DBSETUP="mongo:23234"
#DBSETUP="mongo::persist"
#DBSETUP="mongo:23234:persist"

# OpenMM Simulation Platform
PLATFORM="CUDA"

# Name for AdaptiveMD Project instance
PROJ="chignolin"

# Name of AdaptiveMD sampling function to use
SF="explore_macrostates"

# If you do not generate enough data, the MSM analysis can
# fail, invalidating the end-to-end test. If you get an
# analysis error, try generating more data both for the
# test and real use-cases.

# Number of replicates
N="2"

# Save frequencies. Save protein frequently to increase MSM building data
MFREQ="200"
PFREQ="40"

# MD length per job in steps
Pi="10000"

# Total MD length for full trajectory
Pt="20000"

# Save logs during workflow
export ADMD_SAVELOGS="True"
#------------------------------------------------------------------------------#
#
# Every workload line: need to fill out these options to define a workflow
#  |              0           1           2            3      4      5    
#  | <admd_command> roundnumber projectname workloadtype ntasks nsteps
#  |
#  |      6           7                 8                9      10      11
#  | tsteps afterntrajs minlengthformodel samplingfunction minutes dbsetup
#
# First workload line: needed to initialize AdaptiveMD Project for workflow
#  |         12              13               14                 15
#  | systemname masterfrequency proteinfrequency simulationplatform
#
#------------------------------------------------------------------------------#

admd_checkpoint

#           0 1     2     3  4   5   6 7 8   9    10       11   12     13     14        15
admd_workload 1 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP $SYS $MFREQ $PFREQ $PLATFORM
