# adaptive-sampling
A Python framework to run adaptive Markov state model (MSM) simulation on HPC resources

The generation of MSMs requires a huge amount of trajectory data to be analyzed. In most cases
this leads to an enhanced understanding of the dynamics of the system which can be used to
make decision about collection more data to achieve a desired accuracy or level of detail in
the generated MSM. This alternating process between simulation/actively generating new observations 
and analysis is currently difficult and involves lots of human decision along the path.

This framework aim to automate this process with the following goals:

1. Ease of use: Simple system setup once an HPC has been added.
2. Flexibility: Modular setup, attach to multiple HPCs and different simulation engines
3. Automatism: Create an user-defined adaptive strategy that is executed
4. Compatibility: Build analysis tools and export to known formats


## Prerequisites

There are a few things we need to install to make this work.

### 1. MongoDB

AdaptiveMD and RP both need access to a MongoDB. The FU has one that Allegro can access in place and you can use this for storing projects. If you want to store these locally you need to install MongoDB.

Just download your OS installer from [MongoDB Community Edition](https://www.mongodb.com/download-center#community) and follow the installation instructions. This is very straight forward and should work without any problems. You only need to install MongoDB on your local machine from which you will connect to the cluster. No need to install it on the cluster. 

```bash
curl -O https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian81-3.4.2.tgz
tar -zxvf mongodb-linux-x86_64-debian81-3.4.2.tgz

mkdir -p ~/mongodb
cp -R -n mongodb-linux-x86_64-debian81-3.4.2/ ~/mongodb

# add PATH to .bashrc
echo "export PATH=~/mongodb/bin:$PATH" >> ~/.bash_rc

# create directory for storage (everywhere you have space)
mkdir -p ~/mongodb/data/db

# run the deamon in the background
mongod --quiet --dbpath ~/mongodb/data/db &
```

### 2. Clone adaptive-sampling

Let's get adaptivemd from the github repo now.

```bash
# clone and install adaptive-md 
git clone git@github.com:markovmodel/adaptive-sampling.git
```

### 3. Virtual Environment

For RP you need to create a virtual environment using `virtualenv` 

```bash
# create virtual environment (here named ve)
virtualenv $HOME/ve

# activate it
source $HOME/ve/bin/activate

# install radical.pilot
pip install radical.pilot

# more packages for adaptivemd
pip install pyyaml numpy ujson simtk.unit

# go to adativemd
cd adaptive-sampling/package
# and install it
python setup.py develop

# see if it works
python -c "import adaptivemd" || echo 'FAILED'

# deactivate it
deactivate

# add an alias to .bashrc
echo "alias ve='source $HOME/ve/bin/activate'" >> ~/.bash_rc

```

Note, this is where we run the adaptive sampling strategies from. RP will use the VE to run the pilot that will distribute jobs that we push to the database. The VE is _not_ used to run pyemma or openmm or anything else. This is why we do not have to install it in the VE.

If you want, you can deactivate the VE using

```bash
deactivate
```

### Conda

Whereever you will run the actual tasks (local or a cluster) you probably use some python so we recommend to install the common set of conda packages. If you are remotely executing python then you can even use python 3 without problems. The RPC might also work with python 3 but that needs to be tested. 

If you have not yet installed conda please do so using

```bash
# curl -O https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh
# bash Miniconda2-latest-Linux-x86_64.sh
```

or in analogy for python3

Add 2 useful channels

```bash
conda config --append channels conda-forge
conda config --append channels omnia
```

and `--append` will make sure that the regular conda packages are tried first and use `conda-forge` and `omnia` as a fallback.

Install the usual packages by

```
conda install pyemma openmm mdtraj
```

and install `adaptivemd` from the github using

```
cd adaptive-sampling/package
python setup.py develop
```

All of this must also be installed on the cluster, where you want to run your simulations.

For allegro I suggest to use a miniconda installation. Note that you only need these packages if you want to use some of it on the cluster like run openmm or make computations using pyemma. Just for running, say `acemd` conda is not required!


#### Finally

make sure you run your adaptivemd scripts when the VE is active. There is an alias in the above script

```bash
source $HOME/ve/bin/activate
```

That's it. Have fun running adaptive simulations.

You might want to start with the examples in `package/example/tutorial`