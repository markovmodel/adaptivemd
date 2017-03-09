#!/usr/bin/env bash

# make install dir
mkdir adaptivemd-install
cd adaptivemd-install

curl -O https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian81-3.4.2.tgz
tar -zxvf mongodb-linux-x86_64-debian81-3.4.2.tgz

mkdir -p ~/mongodb
cp -R -n mongodb-linux-x86_64-debian81-3.4.2/ ~/mongodb

echo "export PATH=~/mongodb/bin:$PATH" >> ~/.bash_rc

# install conda
# curl -O https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh
# bash Miniconda2-latest-Linux-x86_64.sh

# add conda channels
conda config --append channels omnia
conda config --append channels conda-forge

# install conda packages
conda install --yes pyemma openmm openmmtools mdtraj ujson pyyaml pymongo=2.8

# create virtual env
virtualenv $HOME/ve
source $HOME/ve/bin/activate

pip install radical.pilot
pip install pyyaml numpy ujson simtk.unit

# install adaptive-md in conda
git clone git@github.com:markovmodel/adaptive-sampling.git
cd adaptive-sampling/package
python setup.py develop

deactivate

python setup.py develop

pip install radical.pilot

cd ../..

# DONE

echo "alias ve='source $HOME/ve/bin/activate'" >> ~/.bash_rc

echo "Use these to (de-)activate the virtual environment"
echo "source $HOME/ve/bin/activate"
echo "deactivate"
