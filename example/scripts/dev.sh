 #!/bin/bash

# Activate virtualenv
source ./.env/bin/activate

# Add drf-sideloading library to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(cd .. && pwd)

# Start development server
python manage.py runserver
