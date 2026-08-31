# Example Project

This is very simple django application using django rest framework
to demonstrate example use ceses and test the `drf_sideloading` library.

The example is a [uv](https://docs.astral.sh/uv/) project and always runs against
the working copy of the library in the parent directory, so there is no need to
export `PYTHONPATH` or install a release from PyPI.

## setup using script

    sh scripts/devsetup.sh

## Run using script

    sh scripts/dev.sh

Visit browser:

    http://127.0.0.1:8000/

Test sideloading products endpoint

    http://127.0.0.1:8000/products/?sideload=categories,suppliers,partners
