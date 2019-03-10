#!/bin/bash

# Mass update all indivudual repos

# To help set echo output in green
green=`tput setaf 2`

# Save the name of all dirs to the dirs variable
dirs=`ls -d */ | grep -v 'venv'`

for dir in $dirs     # list directories in the current folder
do
    #Display dir name 
    echo "${green}${dir}"
    #chain 3 commands in one line below
    cd ${dir} ; git pull ; cd ..
done
