# Example Project

This is very simple django application using django rest framework 
to demonstrate example use ceses and test the `drf_sideloading` library.

This version requires python3 

## Export PYTHONPATH

To use latest version of cloned library export parent directory 

    export PYTHONPATH=$PYTHONPATH:$(cd .. && pwd)

Or install desired release using pip

    pip install drf-sideloading==0.1.7


## setup using script

    sh scripts/devsetup.sh

## Run using script

    sh scripts/dev.sh

Visit browser: 

    http://127.0.0.1:8000/


Test sideloading products endpoint

    http://127.0.0.1:8000/product/?sideload=category,supplier,partner
