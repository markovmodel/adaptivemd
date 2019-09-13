#!/bin/bash

# Folder containing PDB and OpenMM Simulation XML Files
#  - in '$ADMD_ADAPTIVEMD/examples/files/' or user-specified path in "$ADMD_MDSYSTEMS"
SYS="chignolin"

# Walltime for LRMS job
MINS="40"

# Fields separated by colon: "path[:port[:'persistent']]"
#  1. relative or absolute path to DB parent folder
#  2. optional DB port for client-side database
#  3. optional flag to use a persistent, client-side database instance
DBSETUP="mongo:33234:persist"

# OpenMM Simulation Platform
PLATFORM="CUDA"

# Name for AdaptiveMD Project instance
PROJ="chignolin"

# Name of AdaptiveMD sampling function to use
SF="explore_macrostates"

# Save frequencies. Save protein frequently to increase MSM building data
MFREQ="20000"
PFREQ="4000"

# Number of replicates
N="8"

# MD length per job in steps
Pi="1000000"

# Total MD length for full trajectory
Pt="2000000"

# Save logs during workflow
export ADMD_SAVELOGS="True"
#------------------------------------------------------------------------------#
#
# Every workload line: need to fill out these options to define a workflow
#  |   0             1           2            3           4      5    
#  | <admd_command> roundnumber projectname workloadtype ntasks nsteps
#  |
#  |  6      7            8                9                10      11
#  | tsteps afterntrajs minlengthformodel samplingfunction minutes execflag
#
# First workload line: needed to initialize AdaptiveMD Project for workflow
#  |  12          13              14                15
#  | systemname masterfrequency proteinfrequency simulationplatform
#
#------------------------------------------------------------------------------#

admd_checkpoint

#           0 1     2     3  4   5   6 7 8   9    10       11   12     13     14        15
admd_workload 1 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP $SYS $MFREQ $PFREQ $PLATFORM
admd_workload 1 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 1 $PROJ model 1  0   0   0 0 $SF $MINS $DBSETUP

admd_workload 2 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 2 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 2 $PROJ model 1  0   0   0 0 $SF $MINS $DBSETUP
