#!/bin/bash


source $ADMD_RUNTIME/wf_funcs.sh

SYSNAME="alanine"

MINUTES=50
#EXECFLAG="--rp"
#EXECFLAG=/lustre/atlas/proj-shared/bip149/mongodb/pG.db
EXECFLAG="mongo:43224"
PROJ="pG"
MFREQ=10000
PFREQ=2000
PLATFORM=CUDA

N1=50
P1i=1000000
P1t=8000000

# Need to fill out these options to define a workflow
# <admd_command> $ROUNDNUMBER $PROJNAME <workloadtype> $NTRAJ $NSTEPS $TSTEPS $AFTERNTRAJS $MODELTRAJLENGTH $SAMPLINGFUNCTION $MINUTES $EXECFLAG
# TODO define clearly each argument

#------------------#
#    Phase 1       #
#------------------#
checkpoint
admd_workload 1 $PROJ trajs $N1 $P1i $P1t 0 0 explore_macrostates $MINUTES $EXECFLAG $SYSNAME $MFREQ $PFREQ $PLATFORM
admd_workload 1 $PROJNAME trajs $N1 $P1CHUNK $P1LENGTH 0 0 explore_macrostates $MINUTES $EXECFLAG
admd_workload 1 $PROJNAME trajs $N1 $P1CHUNK $P1LENGTH 0 0 explore_macrostates $MINUTES $EXECFLAG
admd_workload 1 $PROJNAME trajs $N1 $P1CHUNK $P1LENGTH 0 0 explore_macrostates $MINUTES $EXECFLAG
admd_workload 1 $PROJNAME trajs $N1 $P1CHUNK $P1LENGTH 0 0 explore_macrostates $MINUTES $EXECFLAG
admd_workload 1 $PROJNAME trajs $N1 $P1CHUNK $P1LENGTH 0 0 explore_macrostates $MINUTES $EXECFLAG
admd_workload 1 $PROJNAME trajs $N1 $P1CHUNK $P1LENGTH 0 0 explore_macrostates $MINUTES $EXECFLAG
admd_workload 1 $PROJNAME trajs $N1 $P1CHUNK $P1LENGTH 0 0 explore_macrostates $MINUTES $EXECFLAG
admd_workload 1 $PROJNAME model 1   0        0         0 0 explore_macrostates $MINUTES $EXECFLAG
# NEXT!
