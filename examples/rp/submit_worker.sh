#!/bin/bash -l

#SBATCH -p micro
#SBATCH --ntasks=1
#SBATCH -t 00:20:00
#SBATCH -J my_job
#SBATCH --cpus-per-task=1
# #SBATCH --ntasks-per-node=1
# #SBATCH --gres=gpu:4

#SBATCH --workdir $HOME/NO_BACKUP/

python worker.py test --sheep testcase-worker-allegro