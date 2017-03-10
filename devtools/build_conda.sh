#!/usr/bin/env bash

# set package data
PACKAGE_NAME=adaptivemd-dev
GROUP_NAME=omnia

# depends whether you use miniconda or anaconda
BUILD_PATH=~/anaconda/conda-bld
BUILD_OS=osx-64

# install conda-build
if conda list | grep conda-build ; then
    conda install --yes conda-build
fi

# build the conda package
conda build conda-recipe

conda install --yes anaconda-client jinja2
conda convert -p all ${BUILD_PATH}/${BUILD_OS}/${PACKAGE_NAME}*.tar.bz2 -o ${BUILD_PATH}/

# this requires your username and password
anaconda upload  --force -u ${GROUP_NAME} -p ${PACKAGE_NAME} ${BUILD_PATH}/*/${PACKAGE_NAME}*.tar.bz2
