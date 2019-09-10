#!/bin/bash

export ADMD_SAVELOGS="True"

SYS="chignolin"
MINS="25"
DBSETUP="mongo:23234:persist"
PLATFORM="CUDA"
PROJ="chignolin"
SF="explore_macrostates"
MFREQ="2000"
PFREQ="400"
N="4"
Pi="100000"
Pt="200000"


#           0 1     2     3  4   5   6 7 8   9    10       11   12     13     14        15
admd_workload 1 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP $SYS $MFREQ $PFREQ $PLATFORM
admd_workload 1 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 1 $PROJ model 1  0   0   0 0 $SF $MINS $DBSETUP

admd_workload 2 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 2 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 2 $PROJ model 1  0   0   0 0 $SF $MINS $DBSETUP

admd_workload 3 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 3 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 3 $PROJ model 1  0   0   0 0 $SF $MINS $DBSETUP

admd_workload 4 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 4 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 4 $PROJ model 1  0   0   0 0 $SF $MINS $DBSETUP

admd_workload 5 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 5 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP
admd_workload 5 $PROJ model 1  0   0   0 0 $SF $MINS $DBSETUP
