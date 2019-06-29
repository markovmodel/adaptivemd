#!/bin/bash

#-------------------------------------------------------------------#
#         Configuration for the installer first
#-------------------------------------------------------------------#
# Environment Setup:
#     Application & Task Runtime:
#       - inside conda env
#
#     You must correctly match the CUDA
#     version on your cluster with OpenMM
#     version via configuration below

USER="osz"
CWD="$(pwd)"
# Line to install AdaptiveMD itself via this
# script, leave empty if you want to do later
INSTALL_ADAPTIVEMD="python setup.py develop"
# TODO mongo via conda, mongo 4.0
MONGO_VERSION="mongodb-linux-x86_64-3.6.11"
CONDA_VERSION="Miniconda3-latest-Linux-x86_64"
PYTHON_VERSION="3.6.6"
PYEMMA_VERSION="pyemma"
# CUDA module line saved in ADMD_PROFILE
CUDA_MODULE="module load cuda/9.2"
OPENMM_VERSION="openmm -c omnia/label/cuda92"

#-------------------------------------------------------------------#
# Software locations configuration
#  - change these for your cluster before running
#    i.e. some clusters have preffered locations
#         for software vs data, and adaptivemd will
#         use different locations for workflow log
#         data vs simulation data

# INSTALL_DIRNAME also the default Conda Env name
INSTALL_DIRNAME="admd"
ADMD_DATA="/lustre/or-hydra/cades-bsd/$USER/$INSTALL_DIRNAME/data"
ADMD_SOFTWARE="/home/$USER/$INSTALL_DIRNAME/software"
ADMD_WORKFLOWS="/lustre/or-hydra/cades-bsd/$USER/$INSTALL_DIRNAME/workflows"
ADMD_MDSYSTEMS="/lustre/or-hydra/cades-bsd/$USER/mdsystems"
ADMD_SAMPLINGFUNCS="/lustre/or-hydra/cades-bsd/$USER/sampling"

# This file contains all required runtime
# environment configuration, built by installer
ADMD_PROFILE="$HOME/admd.bashrc"
touch $ADMD_PROFILE

#-------------------------------------------------------------------#
# Extra actions to include for loading AdaptiveMD Environment
ADMD_ACTIONS[0]="module unload python"
# e.g. if you used a system anaconda module to create this env
#ADMD_ACTIONS[1]="module load python/anaconda"

#-------------------------------------------------------------------#
#             Now onto the installation itself
#-------------------------------------------------------------------#
echo ""
echo "-----------------------------------------------------------"
echo "-----------  AdaptiveMD Installer Components  -------------"
echo ""
echo "    If you want to use a pre-existing MongoDB or Conda"
echo "    you have installed, get it into your path so that"
echo "    a \`which mongod\` and/or \`which conda\` command"
echo "    reports the location before running this script:"
echo ""
echo "PATH=/path/to/mongo/bin:\$PATH"
echo "PATH=/path/to/conda/bin:\$PATH"
echo ""

read -t 1 -n 9999 discard
read -n 1 -p  " --- Type \"y\" if ready to proceed: " proceedinput
if [ ! "$proceedinput" = "y" ]; then
  echo ""
  exit 0
fi

#-------------------------------------------------------------------#
#-------------------------------------------------------------------#
echo ""
echo "-----------------------------------------------------------"
echo "------------- Installing AdaptiveMD Platform --------------"
echo ""
echo ">>>>>>>>>>>> ADMD_PROFILE >>>>>>>>>>>>>>>>>>>>>>>>"
echo "# Source the ADMD_PROFILE when you want to use" | tee -a $ADMD_PROFILE
echo "# your AdaptiveMD Platform" | tee -a $ADMD_PROFILE
echo ""
echo "ADMD_PROFILE=\"$ADMD_PROFILE\"" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "<<<<<<<<<<<< ADMD_PROFILE <<<<<<<<<<<<<<<<<<<<<<<<"
echo ""
echo "    NOTE that it very likely that additional, system"
echo "    specific actions will be required to properly load the"
echo "    environment as you want it."
echo ""
echo "    Work with your system admin to troubleshoot the use of"
echo "    this platform, and include any additional actions here"
echo "    at the top of the RC file by manually modification"
echo ""
echo "    e.g. to use your Conda successfully, you may need to"
echo "         force an unload of a python module"
echo ""
echo "         or if you are using a conda module installed on"
echo "         your cluster, add the module load command"
echo ""
echo "    Contact the developers if you require additional help."
echo ""
echo "    Adding the CUDA_MODULE instruction above to ADMD_PROFILE"
echo ""
echo ">>>>>>>>>>>> ADMD_PROFILE >>>>>>>>>>>>>>>>>>>>>>>>"
echo "# Actions for preparing AdaptiveMD Environment" | tee -a $ADMD_PROFILE
echo "#  - add more below" | tee -a $ADMD_PROFILE
echo "$CUDA_MODULE" | tee -a $ADMD_PROFILE
for action in "${ADMD_ACTIONS[@]}"; do
    echo "$action" | tee -a $ADMD_PROFILE
done
echo "" | tee -a $ADMD_PROFILE
echo "<<<<<<<<<<<< ADMD_PROFILE <<<<<<<<<<<<<<<<<<<<<<<<"
echo ""

read -t 1 -n 9999 discard
read -n 1 -s -r -p " --- Press any key to continue"

#-------------------------------------------------------------------#
#-------------------------------------------------------------------#
echo ""
echo "---------------------------------------------------------"
echo "------------- Creating Platform Directories -------------"
echo ""
echo ">>>>>>>>>>>> ADMD_PROFILE >>>>>>>>>>>>>>>>>>>>>>>>"
echo "# AdaptiveMD Platform Location Configurations" | tee -a $ADMD_PROFILE
echo "ADMD_DATA=\"$ADMD_DATA\"" | tee -a $ADMD_PROFILE
echo "ADMD_SOFTWARE=\"$ADMD_SOFTWARE\"" | tee -a $ADMD_PROFILE
echo "ADMD_WORKFLOWS=\"$ADMD_WORKFLOWS\"" | tee -a $ADMD_PROFILE
echo "ADMD_MDSYSTEMS=\"$ADMD_MDSYSTEMS\"" | tee -a $ADMD_PROFILE
echo "ADMD_SAMPLINGFUNCS=\"$ADMD_SAMPLINGFUNCS\"" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "<<<<<<<<<<<< ADMD_PROFILE <<<<<<<<<<<<<<<<<<<<<<<<"
mkdir -p "$ADMD_DATA"
mkdir -p "$ADMD_SOFTWARE"
mkdir -p "$ADMD_WORKFLOWS"
mkdir -p "$ADMD_MDSYSTEMS"
mkdir -p "$ADMD_SAMPLINGFUNCS"

#-------------------------------------------------------------------#
#-------------------------------------------------------------------#
echo ""
echo "---------------------------------------------------------"
echo "--------------- MongoDB Component Install ---------------"
echo ""
cd $ADMD_SOFTWARE
if [ -z "$(command -v mongod)" ]; then
  mongodb="https://fastdl.mongodb.org/linux/${MONGO_VERSION}.tgz"
  echo "Downloading: $mongodb"
  wget "$mongodb"
  tar -zxvf "${MONGO_VERSION}.tgz" -C "./"
  mv "$MONGO_VERSION" "mongodb"
  rm "${MONGO_VERSION}.tgz"
  PATH="$ADMD_SOFTWARE/mongodb/bin:$PATH"
else
  echo "Skipping MongoDB download, found this \`mongod\`"
  echo "and adding it to $ADMD_PROFILE"
  echo "$(which mongod)"
fi

echo ">>>>>>>>>>>> ADMD_PROFILE >>>>>>>>>>>>>>>>>>>>>>>>"
echo "# AdaptiveMD Platform PATH Configurations" | tee -a $ADMD_PROFILE
echo "export PATH=\"$(dirname $(which mongod)):\$PATH\"" | tee -a $ADMD_PROFILE
echo "<<<<<<<<<<<< ADMD_PROFILE <<<<<<<<<<<<<<<<<<<<<<<<"
echo ""

#-------------------------------------------------------------------#
#-------------------------------------------------------------------#
echo ""
echo "-----------------------------------------------------------"
echo "--------------- Miniconda Component Install ---------------"
echo ""
cd $ADMD_SOFTWARE
if [ -z "$(command -v conda)" ]; then
  miniconda="https://repo.continuum.io/miniconda/${CONDA_VERSION}.sh"
  echo "Downloading: $miniconda"
  wget "$miniconda"
  bash "${CONDA_VERSION}.sh" -b -p miniconda
  rm   "${CONDA_VERSION}.sh"
  PATH="$ADMD_SOFTWARE/miniconda/bin:$PATH"
else
  echo "Skipping Miniconda download, found this \`conda\`."
  echo "Will add it to $ADMD_PROFILE"
  echo "$(which conda)"
fi

conda config --add channels omnia --add channels conda-forge
conda update --yes --all -n base -c defaults conda
conda init bash

#-------------------------------------------------------------------#
#-------------------------------------------------------------------#
echo ""
echo "-----------------------------------------------------------"
echo "---------------- Conda Environment Setup ------------------"
echo ""
echo "Creating new conda env \"$INSTALL_DIRNAME\""
echo "with AdaptiveMD Simulation and Analysis stack"

read -t 1 -n 9999 discard
read -n 1 -p  " --- Press [enter] to keep this name, or type a new one: " proceedinput
echo ""

if [ ! -z "$proceedinput" ]; then
  ENV_NAME="$proceedinput"
else
  ENV_NAME="$INSTALL_DIRNAME"
fi

conda create  --yes -n $ENV_NAME python=$PYTHON_VERSION
source activate $ENV_NAME
conda install --yes $OPENMM_VERSION
conda install --yes $PYEMMA_VERSION

echo ">>>>>>>>>>>> ADMD_PROFILE >>>>>>>>>>>>>>>>>>>>>>>>"
echo "export PATH=\"$(dirname $(which conda)):\$PATH\"" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "<<<<<<<<<<<< ADMD_PROFILE <<<<<<<<<<<<<<<<<<<<<<<<"

cd "$CWD"

#-------------------------------------------------------------------#
#-------------------------------------------------------------------#
if [ ! -z "$INSTALL_ADAPTIVEMD" ]; then
    echo "AdaptiveMD Environment is installed,"
    echo "finishing up by installing the"
    echo "AdaptiveMD Python Package now with"
    echo "this line:"
    echo "$INSTALL_ADAPTIVEMD"
    eval "$INSTALL_ADAPTIVEMD"
else
    echo "AdaptiveMD Environment is installed"
    echo "but you have chosen to install the"
    echo "AdaptiveMD Python Package separately"
fi

echo ""

#-------------------------------------------------------------------#
#           Done, just printing some useful info
#-------------------------------------------------------------------#
echo "-----------------------------------------------------------"
echo "--------------------   Install is Done    -----------------"
echo ""
echo "To read AdaptiveMD environment profile, use"
echo "source $ADMD_PROFILE"
echo ""
echo "Conda env name: \"$ENV_NAME\""
echo ""
echo "To use the environment, first source the AdaptiveMD"
echo "profile and then source the environment:"
echo "source activate $ENV_NAME"
echo ""
echo "-----------------------------------------------------------"
