#!/bin/bash -l
# Submission for allegro with a full node and 4 GPUs using a single process

#SBATCH -p gpu
#SBATCH --ntasks=1
#SBATCH -t 00:20:00
#SBATCH -J 4gpu_adaptivemd
#SBATCH -N 1
#SBATCH --gres=gpu:4

#SBATCH --workdir /home/jprinz/NO_BACKUP

PROJECT_NAME=example-worker
DB_PATH=sheep

# run 4 workers which will all use a different CUDA device
adaptivemdworker --wrapper="setenv('CUDA_DEVICE_INDEX', '0')" -d mongodb://$DB_PATH:27017 $PROJECT_NAME &
adaptivemdworker --wrapper="setenv('CUDA_DEVICE_INDEX', '1')" -d mongodb://$DB_PATH:27017 $PROJECT_NAME &
adaptivemdworker --wrapper="setenv('CUDA_DEVICE_INDEX', '2')" -d mongodb://$DB_PATH:27017 $PROJECT_NAME &
adaptivemdworker --wrapper="setenv('CUDA_DEVICE_INDEX', '3')" -d mongodb://$DB_PATH:27017 $PROJECT_NAME &

wait