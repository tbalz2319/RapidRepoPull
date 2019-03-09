#!/bin/bash

#Install all the requirements for the RapidRepoPull program and run

# Set virtual env with Python3
python3 -m venv venv

# Activate virtual env
source venv/bin/activate

# Upddate virtual pip version
pip install --upgrade pip

# Install requirements file
pip install -r requirements.txt

# Execute script
python3 rapid.py

