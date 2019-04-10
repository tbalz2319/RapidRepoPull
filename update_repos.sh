#!/bin/bash

# Mass update all indivudual repos

# To help set echo output in green
green=$(tput setaf 2)

# Save the name of all dirs to the dirs variable
# The grep -v 'venv' will remove the venv directory as it does not have
# Any repos the user would need to clone 
dirs=`ls -d */ | grep -v 'venv'`

for dir in $dirs     # list directories in the current folder
do
    #Display dir name and cd into dir and cd .. using a subshell
    (
    echo "${green}${dir}"
    cd ${dir} || exit 
    git pull
    )
done
