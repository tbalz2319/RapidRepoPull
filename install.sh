#!/usr/bin/env bash

# Install all the requirements for the RapidRepoPull program and run

# Install required packages based on running OS


# if [ "$(uname)" == "Darwin" ]; then
#     # Do something under Mac OS X platform        
# elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
#     # Do something under GNU/Linux platform
#     # The if statement below will only work on Linux (Ubuntu/Debian/Kali) based distros
#     # It will not work with (Fedora/RHEL/Centos) distros
#     pkgs='python3-venv git'
#     if ! dpkg -s $pkgs >/dev/null 2>&1; then
#          sudo apt-get install $pkgs
#     fi
# elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ]; then
#     # Do something under 32 bits Windows NT platform
# elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW64_NT" ]; then
#     # Do something under 64 bits Windows NT platform
# fi

green=$(tput setaf 2)
cyan=$(tput setaf 6)

# Set virtual env with Python3
echo "${green}Setting up Python3 virtual env"
python3 -m venv venv

# Activate virtual env
echo "${cyan}Activating virtaul env"
source venv/bin/activate

# Upddate virtual pip version
echo "${cyan}Upgrading virtual pip version"
pip install --upgrade pip

# Install requirements file
pip install -r requirements.txt

# Execute script with all the default options
time python rapid.py -t 50

