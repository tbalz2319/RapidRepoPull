#!/bin/bash

# Mass update all indivudual repos
dirs=`ls -d */ | grep -v 'venv'`

for dir in $dirs     # list directories in the current folder
do
    #echo $dir
    cd ${dir} ; git pull ; cd ..
done
