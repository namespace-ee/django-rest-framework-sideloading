#!/bin/bash

set -e

# Install the example against the working copy of drf-sideloading
uv sync

# Run migrate
uv run python manage.py migrate

# Load example data from fixtures
uv run python manage.py loaddata products/fixtures/products.json
