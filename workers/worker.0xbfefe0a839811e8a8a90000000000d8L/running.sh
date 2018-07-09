set -e
ln -s ../staging_area/alanine.pdb initial.pdb
ln -s ../staging_area/system.xml system.xml
ln -s ../staging_area/integrator.xml integrator.xml
ln -s ../staging_area/openmmrun.py openmmrun.py
mkdir -p traj/

j=0
tries=10
sleep=1

trajfile=traj/protein.dcd

while [ $j -le $tries ]; do if ! [ -s $trajfile ]; then python openmmrun.py -r --report-interval 1 -p CPU --types="{'protein':{'stride':1,'selection':'protein','name':null,'filename':'protein.dcd'},'master':{'stride':10,'selection':null,'name':null,'filename':'master.dcd'}}" -s system.xml -i integrator.xml -t initial.pdb --length 100 traj/; fi; sleep 1; j=$((j+1)); done
mkdir -p ../../projects/tutorial/trajs/00000000/
mv traj/* ../../projects/tutorial/trajs/00000000/
rm -r traj/