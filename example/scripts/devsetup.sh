#!/bin/bash

set -e

# Create the virtualenv and install the example project together with the
# working copy of drf-sideloading. uv fetches Python itself if needed.
uv sync

# Run migrate
uv run python manage.py migrate

# Load example data from fixtures
uv run python manage.py loaddata products/fixtures/products.json
