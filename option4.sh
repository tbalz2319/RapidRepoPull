#!/bin/bash

#Install all the requirements for the RapidRepoPull program and run for option4

green=`tput setaf 2`

# Set virtual env with Python3
echo "${green}Setting up Python3 virtual env"
python3 -m venv venv

# Activate virtual env
echo "${green}Activating virtual env"
source venv/bin/activate

# Upddate virtual pip version
echo "${green}Upgrading virtual pip version"
pip install --upgrade pip

# Install requirements file
pip install -r requirements.txt

# At this point the program is ready to run
# Adding a few spcaces below
echo "  "
echo "  "
echo "  "
echo "  "
echo "  "
echo "  "
echo "  "
echo "  "
echo "  "

# Display help options
python rapid.py --help 

# Ensure virtualenv is active after this script exits
echo "${green}Activating virtual env via Python script..."
python activate_venv.py

