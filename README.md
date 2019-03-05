# RapidRepoPull

![os](https://img.shields.io/badge/OS-Linux,%20macOS-yellow.svg)
![rapidrepoinstallver](https://img.shields.io/badge/version-1.3.2-red.svg)
[![Twitter](https://img.shields.io/badge/twitter-@xtbalz-blue.svg)](https://twitter.com/xtbalz)
[![CodeFactor](https://www.codefactor.io/repository/github/tbalz2319/rapidrepopull/badge)](https://www.codefactor.io/repository/github/tbalz2319/rapidrepopull)
[![Build Status](https://travis-ci.com/tbalz2319/RapidRepoPull.svg?token=QYYAGdpg1FpLiGsNAJgb&branch=master)](https://travis-ci.com/tbalz2319/RapidRepoPull)

## Description

- This program uses Python to clone multiple security related repos using threading and multiprocessing

## Goal

- The goal of this program is to quickly pull and install repos from its list

## Use cases

- Quickly install your favorite Security repos on a new system

- Kick off multiple concurrent tasks utilizing Python

- Add remove lists as your see fit to meet your needs

## Requirements

- This program was tested with Python version 3.7.2 64-bit

- Ensure the Python3 virtual environment package is installed (Ubuntu)

    ```sudo apt-get install python3-venv```

- Ensure git is installed (Ubuntu)

    ```sudo apt-get install git```

## Usage

- Clone code repo

    ```git clone https://github.com/tbalz2319/RapidRepoPull.git```

- Change directory into RapidRepoPull

    ```cd RapidRepoPull```

- Create a virtual Python3 environment to run this code

    ```python3 -m venv venv```

- Activate the virual enivornment

    ```source venv/bin/activate```

- Install requirements

    ```pip install -r requirements.txt```

- Run program

    ```python3 rapid.py```

## To do

- Add error handling

- Clean up code

- Create install shell script for ease of use

## Contribute

- Code is being cleaned up and refined, there are most likely lots of bugs that need to fixed

- Pull requests welcomed
