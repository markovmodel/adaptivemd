# adaptiveMD
A Python framework to run adaptive MD simulations using Markov state model (MSM)
analysis on HPC resources.

The generation of MSMs requires a huge amount of trajectory data to be analyzed.
In most cases this leads to an enhanced understanding of the dynamics of the
system, which can be used to make decisions about collecting more data to
achieve a desired accuracy or level of detail in the generated MSM. This
alternating process between simulation and actively generating new observations
& analysis is currently difficult and involves human decision along the path.

This framework aim to automate this process with the following goals:

1. Ease of use: Simple system setup once an HPC resource has been added.
2. Flexibility: Modular setup of multiple HPCs and different simulation engines
3. Automatism: Create an user-defined adaptive strategy that is executed
4. Compatibility: Build analysis tools and export to known formats


After installation, you might want to start working with the examples
in `examples/tutorials`.


## Prerequisites

There are a few things we need to install to make this work.

### MongoDB

AdaptiveMD needs access to a MongoDB. If you want to store project data locally
you need to install MongoDB. Both your user machine and compute resource must
see the databse.

[MongoDB Community Edition](https://www.mongodb.com/download-center#community)
will provide your OS installer, just download and follow the installation
instructions. This is straight forward and should work without any problems.
Depending on the compute resource restrictions, it might be necessary to install
the database in different locations.
**You only need to install MongoDB on your local machine from which you will
connect to the cluster. No need to install the database on the cluster.**
- only if the compute nodes can see the 'local' drive


For linux systems:
```bash
curl -O https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian81-3.4.2.tgz
tar -zxvf mongodb-linux-x86_64-debian81-3.4.2.tgz

mkdir ~/mongodb
cp -R -n mongodb-linux-x86_64-debian81-3.4.2/ ~/mongodb

# add PATH to .bashrc
echo "export PATH=~/mongodb/mongodb-linux-x86_64-debian81-3.4.2/bin/:\$PATH" >> ~/.bashrc

# create directory for storage
mkdir -p ~/mongodb/data/db

# run the deamon in the background
mongod --quiet --dbpath ~/mongodb/data/db &
```

### Conda

Whereever you will run the actual tasks (local or a cluster) you probably use
some python so we recommend to install the common set of conda packages. If you
are remotely executing python then you can even use python 3 without problems.
The RPC might also work with python 3 but that needs to be tested. 

If you have not yet installed conda please do so using

```bash
# curl -O https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh
# bash Miniconda2-latest-Linux-x86_64.sh
```

or for a python3 version

```bash
# curl -O https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
# bash Miniconda3-latest-Linux-x86_64.sh
```

Add 2 useful channels

```bash
conda config --append channels conda-forge
conda config --append channels omnia
```

`--append` will make sure that the regular conda packages are tried first, then
use `conda-forge` and `omnia` as a fallback.

Install required and necessary packages now

```bash
# for adaptivemd only
conda install ujson pyyaml pymongo=2.8 numpy

# for using python 3
conda install pymongo=3.3

# for openmm, pyemma etc
conda install pyemma openmm mdtraj
```

### Install _adaptiveMD_

Let's get adaptivemd from the github repo now.

```bash
# clone and install adaptivemd 
git clone git@github.com:markovmodel/adaptivemd.git

# go to adativemd
cd adaptivemd/

# and install it
python setup.py develop

# see if it works
python -c "import adaptivemd" || echo 'FAILED'

# run the mongodb server if not running already
mongod --dbpath={path_to_your_db_folder}

# run a simple test
cd adaptivemd/tests/
python test_simple.py

```

All of this must also be installed on the cluster, where you want to run your
simulations.

For allegro I suggest to use a miniconda installation. Note that you only need
these packages if you want to use some of it on the cluster like run openmm or
make computations using pyemma. Just for running, say `acemd`, conda is not
required!

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
