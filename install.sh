#!/bin/bash

# Install all the requirements for the RapidRepoPull program and run

# Install required packages
# The if statement below will only work on Linux (Ubuntu/Debian/Kali) based distros
pkgs='python3-venv git'
if ! dpkg -s $pkgs >/dev/null 2>&1; then
  sudo apt-get install $pkgs
fi

green=`tput setaf 2`

# Set virtual env with Python3
echo "${green}Setting up Python3 virtual env"
python3 -m venv venv

# Activate virtual env
echo "${green}Activating virtaul env"
source venv/bin/activate

# Upddate virtual pip version
echo "${green}Upgrading virtual pip version"
pip install --upgrade pip

# Install requirements file
pip install -r requirements.txt

# Execute script
time python rapid.py

