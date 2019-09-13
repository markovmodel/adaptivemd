#!/bin/bash

export ADMD_SAVELOGS="True"

SYS="chignolin"
MINS="15"
DBSETUP="mongo:33234:persist"
PLATFORM="CUDA"
PROJ="chignolin"
SF="explore_macrostates"
N="4"
MFREQ="20000"
PFREQ="4000"
Pi="500000"
Pt="1000000"

admd_checkpoint
admd_workload 1 $PROJ trajs $N $Pi $Pt 0 0 $SF $MINS $DBSETUP $SYS $MFREQ $PFREQ $PLATFORM
