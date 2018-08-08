[![Build Status](https://travis-ci.org/jrossyra/adaptivemd.svg?branch=rp_integration)](https://travis-ci.org/jrossyra/adaptivemd)

# AdaptiveMD

A Python framework to run adaptive MD simulations using Markov State Model (MSM)
analysis on HPC resources.

- See below for a simple installation
- Configure & run `install_admd.sh` to deploy on HPC or cluster

The generation of MSMs requires a huge amount of trajectory data to be analyzed.
In most cases this leads to an enhanced understanding of the dynamics of the
system, which can be used to make decisions about collecting more data to
achieve a desired accuracy or level of detail in the generated MSM. This
alternating process between simulation to actively generate new observations
& analysis is currently difficult and involves human decision along the path.

AdaptiveMD aims to simplify this process with the following design goals:

1. Ease of use: Simple system setup once an HPC resource has been added.
2. Flexibility: Modular setup of multiple HPCs and different simulation engines
3. Automatism: Create a user-defined adaptive strategy that is executed
4. Compatibility: Build analysis tools and export to known formats

After installation, you might want to start working with the examples in `examples/tutorials`. You will first learn the basics of how tasks are created and executed, and then more on composing workflows.


## Prerequisites

There are a few components we need to install for `AdaptiveMD` to work. If you are installing in a regular workstation environment, you can follow the instructions below or use the installer script. If you are installing in a cluster or HPC environment, we recommend you use the script `install_admd.sh`.  The instructions here in the README should give you the gist of what's going on in the installer, which sets up the same components but does more configuration of the environment used by`AdaptiveMD`.

AdaptiveMD creates task descriptions that can be executed using a native `worker` object or via the RADICAL-Pilot execution framework. """RP install configuration on or off"""

### MongoDB

`AdaptiveMD` needs access to a MongoDB. If you want to store project data locally
you need to install MongoDB. Both your user machine and compute resource (where tasks are executed) must see a port used by the database.

[MongoDB Community Edition](https://www.mongodb.com/download-center#community)
will provide an installer for your OS, just download and follow the installation instructions. Depending on the compute resource network restrictions, it might be necessary to install the database in different locations for production workflows.

For linux systems:
```bash
curl -O https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian81-3.4.2.tgz
tar -zxvf mongodb-linux-x86_64-debian81-3.4.2.tgz
mkdir ~/mongodb
mv mongodb-linux-x86_64-debian81-3.4.2/ ~/mongodb
# add mongodb binaries to PATH in .bashrc
echo "export PATH=~/mongodb/mongodb-linux-x86_64-debian81-3.4.2/bin/:\$PATH" >> ~/.bashrc
# create parent directory for database
mkdir -p ~/mongodb/data/db
# run a `mongod` deamon in the background
mongod --quiet --dbpath ~/mongodb/data/db &
```

### Conda

We recommend using contained python environments to run `AdaptiveMD`. The `AdaptiveMD` application environment can be considered separate from the task-execution environment, but for simplicity in these instructions we will load the same environment in tasks that is used when running the application. This means that `AdaptiveMD`, along with the task 'kernels' `OpenMM` and `PyEMMA` are all installed in a single environment.

Conda provides a complete and self-contained python installation that prevents all sorts of problems with software installation & compatibility, so we recommend it to get started. When you move to a cluster or HPC environment, it will likely be a better choice to use `virtualenv` as your environment container. It uses an existing python installation with env-specific libraries, and is thus faster to load and more scalable, but does not resolve installation issues as thoroughly. 

If you do not yet have conda installed, do so using:

```bash
curl -O https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

Add 2 useful channels
```bash
conda config --append channels conda-forge
conda config --append channels omnia
```

`--append` will make sure that the regular conda packages are tried first, then
use `conda-forge` and `omnia` as a fallback.

Install required packages now:

```bash
# be sure the conda python version is fully updated
conda install python
# create a new conda environment for all the installations
conda create -n admdenv python=2.7
source activate admdenv
```

Now installing adaptiveMD related packages. Note you must be inside the python environment you will be working in when installing the packages (or use: `conda install -n [packages...]`):

```bash
# jupyter notebook for tutorials and project work
conda install jupyter
# to prep for adaptivemd install
conda install pyyaml
# for simulations & analysis
# since we're using same env for tasks
conda install pyemma openmm
```

### Install _AdaptiveMD_

Let's get adaptivemd from the github repo now.

```bash
# clone and install adaptivemd 
git clone https://github.com:markovmodel/adaptivemd.git

# go to adativemd and install it
cd adaptivemd/
python setup.py install
#OR
#pip install .
# see if we pass the import test
python -c "import adaptivemd" || echo 'FAILED'

# run a simple test
cd adaptivemd/tests/
#FIXME
python test_simple.py
```

`pyemma` and `openmm` should
be installed on the compute resource as well as the local machine. It is
possible to exclude, say, `openmm` from the local install if simulations will
only be run on the resource. 

That's it. Have fun running adaptive simulations.

#### Documentation

To compile the doc pages, clone this github repository, go into the `docs`
folder and do

```bash 
conda install sphinx sphinx_rtd_theme pandoc
make html
```

The HTML pages are in _build/html. Please note that the docs can only be
compiled if all the above mentionend AdaptiveMD dependencies are available.
If you are using conda environments, this means that your AdaptiveMD
environment should be active.
