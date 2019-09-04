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

#USER="jrossyra"
CWD="$(pwd)"

# Line to install AdaptiveMD itself via this
# script, leave empty if you want to do later
INSTALL_ADAPTIVEMD="python setup.py develop"

# Type "yes" here to build the chignolin test system
#  - installs `parmed` and uses Charmm22star forcefield
BUILD_CHIGNOLIN="yes"

# TODO mongo via conda, mongo 4.0

MONGO_VERSION="mongodb-linux-x86_64-3.6.13"
#MONGO_VERSION="mongodb-linux-x86_64-3.2.22"
CONDA_VERSION="Miniconda3-latest-Linux-x86_64"
PYTHON_VERSION="3.7"
PYEMMA_VERSION="pyemma"
OPENMM_VERSION="openmm -c omnia/label/cuda100"

# CUDA module line saved in ADMD_PROFILE
CUDA_MODULE="module load cuda"

# Runtime preferences and specifics for your cluster
ADMD_LOGLEVEL="INFO"
ADMD_NETDEVICE="eth0"

#-------------------------------------------------------------------#
# Software locations configuration
#  - change these for your cluster before running
#    i.e. some clusters have preffered locations
#         for software vs data, and adaptivemd will
#         use different locations for workflow log
#         data vs simulation data

# INSTALL_DIRNAME also the default Conda Env name
INSTALL_DIRNAME="admd"
ADMD_DATA="/gpfs/alpine/proj-shared/bif112/$USER/$INSTALL_DIRNAME/data"
ADMD_SOFTWARE="/gpfs/alpine/proj-shared/bif112/$USER/$INSTALL_DIRNAME/software"
ADMD_WORKFLOWS="/gpfs/alpine/proj-shared/bif112/$USER/$INSTALL_DIRNAME/workflows"
ADMD_MDSYSTEMS="/gpfs/alpine/proj-shared/bif112/$USER/$INSTALL_DIRNAME/mdsystems"
ADMD_SAMPLINGFUNCS="/gpfs/alpine/proj-shared/bif112/$USER/$INSTALL_DIRNAME/sampling"

# This file contains all required runtime
# environment configuration, built by installer
ADMD_PROFILE="$HOME/admd-rhea.bashrc"
touch $ADMD_PROFILE

#-------------------------------------------------------------------#
# Extra actions to include for loading AdaptiveMD Environment
ADMD_ACTIONS[0]="module unload python"
#ADMD_ACTIONS[1]="module load PE-gnu"
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
echo "export ADMD_PROFILE=\"$ADMD_PROFILE\"" | tee -a $ADMD_PROFILE
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

echo ">>>>>>>>>>>> ADMD_PROFILE >>>>>>>>>>>>>>>>>>>>>>>>"
echo "# AdaptiveMD Environment Runtime Settings" | tee -a $ADMD_PROFILE
echo "#  - modify to match the compute node interconnect" | tee -a $ADMD_PROFILE
echo "#  - and your output level needs" | tee -a $ADMD_PROFILE
echo "export ADMD_LOGLEVEL=\"$ADMD_LOGLEVEL\"" | tee -a $ADMD_PROFILE
echo "export ADMD_NETDEVICE=\"$ADMD_NETDEVICE\"" | tee -a $ADMD_PROFILE
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
echo "export ADMD_DATA=\"$ADMD_DATA\"" | tee -a $ADMD_PROFILE
echo "export ADMD_SOFTWARE=\"$ADMD_SOFTWARE\"" | tee -a $ADMD_PROFILE
echo "export ADMD_WORKFLOWS=\"$ADMD_WORKFLOWS\"" | tee -a $ADMD_PROFILE
echo "export ADMD_MDSYSTEMS=\"$ADMD_MDSYSTEMS\"" | tee -a $ADMD_PROFILE
echo "export ADMD_ADAPTIVEMD=\"$CWD\"" | tee -a $ADMD_PROFILE
echo "export ADMD_SAMPLINGFUNCS=\"$ADMD_SAMPLINGFUNCS\"" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "# This var is defined (and redefined) when using the runtime" | tee -a $ADMD_PROFILE
echo "# system so all the platform layers can find database" | tee -a $ADMD_PROFILE
echo "#ADMD_DBURL=\"mongodb://localhost:27017\"" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "<<<<<<<<<<<< ADMD_PROFILE <<<<<<<<<<<<<<<<<<<<<<<<"

mkdir -p "$ADMD_DATA"
mkdir -p "$ADMD_SOFTWARE"
mkdir -p "$ADMD_WORKFLOWS"
mkdir -p "$ADMD_MDSYSTEMS"
mkdir -p "$ADMD_SAMPLINGFUNCS"

touch "$ADMD_SAMPLINGFUNCS/__init__.py"
touch "$ADMD_SAMPLINGFUNCS/user_functions.py"

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
  ADMD_ENV_NAME="$proceedinput"
else
  ADMD_ENV_NAME="$INSTALL_DIRNAME"
fi

conda create  --yes -n $ADMD_ENV_NAME python=$PYTHON_VERSION
source activate $ADMD_ENV_NAME
conda install --yes $OPENMM_VERSION
conda install --yes $PYEMMA_VERSION

# something weird goes on with the yaml and pyyaml
conda install --yes --force-reinstall pyyaml

echo ">>>>>>>>>>>> ADMD_PROFILE >>>>>>>>>>>>>>>>>>>>>>>>"
echo "export PATH=\"$ADMD_SOFTWARE/miniconda/bin:\$PATH\"" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "# 'activate' now in PATH" | tee -a $ADMD_PROFILE
echo "# TODO maybe? conda activate $ADMD_ENV_NAME... but seems" | tee -a $ADMD_PROFILE
echo "#      this isn't reliable without the bashrc component" | tee -a $ADMD_PROFILE
echo "export ADMD_ACTIVATE=\"source activate $ADMD_ENV_NAME\"" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "# activate by default" | tee -a $ADMD_PROFILE
echo "\$ADMD_ACTIVATE" | tee -a $ADMD_PROFILE
echo "" | tee -a $ADMD_PROFILE
echo "<<<<<<<<<<<< ADMD_PROFILE <<<<<<<<<<<<<<<<<<<<<<<<"

cd "$CWD"

# FIXME TODO I have seen that at least on some machines,
#            the OpenMM / Simtk packages aren't importable
#            some times, not others, no idea why, without
#            a deactivate and reactivate of the env
source deactivate $ADMD_ENV_NAME
source   activate $ADMD_ENV_NAME

#-------------------------------------------------------------------#
#-------------------------------------------------------------------#
if [ ! -z "$INSTALL_ADAPTIVEMD" ]; then
    echo "AdaptiveMD Environment is installed,"
    echo "finishing up by installing the"
    echo "AdaptiveMD Python Package now with"
    echo "this line:"
    echo "$INSTALL_ADAPTIVEMD"
    eval "$INSTALL_ADAPTIVEMD"

    # Build the alanine system for lightweight basic tests
    cd "examples/files/alanine"
    python "openmmsetup.py"
    cd $CWD
else
    echo "AdaptiveMD Environment is installed"
    echo "but you have chosen to install the"
    echo "AdaptiveMD Python Package separately"
fi

if [ "$BUILD_CHIGNOLIN" = "yes" ]; then
    conda install --yes parmed
    cd "examples/files/chignolin/"
    ./parmit.py
    cd "$CWD"
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
echo "Conda env name: \"$ADMD_ENV_NAME\""
echo ""
echo "To use the environment, first source the AdaptiveMD"
echo "profile and then source the environment:"
echo "source activate $ADMD_ENV_NAME"
echo " --or--"
echo "conda activate $ADMD_ENV_NAME"
echo ""
echo "-----------------------------------------------------------"
