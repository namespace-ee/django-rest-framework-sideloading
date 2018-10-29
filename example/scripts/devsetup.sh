#!/bin/bash

set -e

## Python setup
# create venv if not there (use venv)
python3 -m venv --prompt "${PROJECT_NAME}" .env
# activate it
source ./.env/bin/activate

# Automate one of the ways of using library in example project
# export PYTHONPATH=$PYTHONPATH:$(cd .. && pwd)
# pip install drf-sideloading

# install requirements
pip install -r requirements.txt

# migrate
python manage.py migrate

#Load data
python manage.py loaddata products/fixtures/products.json
