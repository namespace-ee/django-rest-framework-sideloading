=============================
drf-sideloading
=============================

.. image:: https://badge.fury.io/py/drf-sideloading.svg
    :target: https://badge.fury.io/py/drf-sideloading

.. image:: https://travis-ci.org/namespace-ee/drf-sideloading.svg?branch=master
    :target: https://travis-ci.org/namespace-ee/drf-sideloading

.. image:: https://codecov.io/gh/namespace-ee/drf-sideloading/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/namespace-ee/drf-sideloading

Extention for Django Rest Framework to enable simple sidloading

Documentation
-------------

The full documentation is at https://drf-sideloading.readthedocs.io.

Quickstart
----------

Install drf-sideloading::

    pip install drf-sideloading

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'drf_sideloading.apps.DrfSideloadingConfig',
        ...
    )

Add drf-sideloading's URL patterns:

.. code-block:: python

    from drf_sideloading import urls as drf_sideloading_urls


    urlpatterns = [
        ...
        url(r'^', include(drf_sideloading_urls)),
        ...
    ]

Features
--------

* TODO

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
