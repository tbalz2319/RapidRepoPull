#!/bin/bash

# Install Empire and setup API

cd Empire/setup && ./install.sh && cd ..
# Start the Empire console and RESTful API
python empire --rest --username empireadmin --password Password123