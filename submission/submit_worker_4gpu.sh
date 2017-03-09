#!/bin/bash -l
# Submission for allegro with a full node and 4 GPUs using a single process

#SBATCH -p gpu
#SBATCH --ntasks=1
#SBATCH -t 00:20:00
#SBATCH -J 4gpu_adaptivemd
#SBATCH --cpus-per-task=1
#SBATCH -n 1
#SBATCH --gres=gpu:4

#SBATCH --workdir $HOME/NO_BACKUP/

PROJECT_NAME={your_project_name}

# run 4 workers which will all use a different CUDA device
python worker.py --wrapper="setenv('CUDA_DEVICE_INDEX', '0')" -d mongodb://path.to.mongodb.server:27017 $PROJECT_NAME &
python worker.py --wrapper="setenv('CUDA_DEVICE_INDEX', '1')" -d mongodb://path.to.mongodb.server:27017 $PROJECT_NAME &
python worker.py --wrapper="setenv('CUDA_DEVICE_INDEX', '2')" -d mongodb://path.to.mongodb.server:27017 $PROJECT_NAME &
python worker.py --wrapper="setenv('CUDA_DEVICE_INDEX', '3')" -d mongodb://path.to.mongodb.server:27017 $PROJECT_NAME &

wait