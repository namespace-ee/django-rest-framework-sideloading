#!/bin/bash

set -e

# Create venv if not there (use venv)
python3 -m venv --prompt "${PROJECT_NAME}" .env

# Activate virtualenv
source ./.env/bin/activate

# Add drf-sideloading library to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(cd .. && pwd)

# Install requirements
pip install -r requirements.txt

# Run migrate
python manage.py migrate

# Load example data from fixtures
python manage.py loaddata products/fixtures/products.json
