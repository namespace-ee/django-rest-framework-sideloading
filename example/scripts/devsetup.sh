#!/bin/bash

set -e

## Python setup
# create venv if not there (use venv)
python3 -m venv --prompt "${PROJECT_NAME}" .venv
# activate it
source ./.venv/bin/activate

# install reuirements
pip install -r requirements.txt

# migrate
python manage.py migrate


# do other setups if needed
