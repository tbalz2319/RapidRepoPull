#!/usr/bin/env bash

#  Arm all the requirements for the RapidRepoPull to execute

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

# Ensure virtualenv is active after this script exits
echo "${green}Activating virtual env via Python script..."
python activate_venv.py

echo "RapidRepoPull is ARMED and ready for testing..."