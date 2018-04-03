=============================
drf-sideloading
=============================

.. image:: https://badge.fury.io/py/drf-sideloading.svg
    :target: https://badge.fury.io/py/drf-sideloading
    :alt: Package Index

.. image:: https://travis-ci.org/namespace-ee/django-rest-framework-sideloading.svg?branch=master
    :target: https://travis-ci.org/namespace-ee/django-rest-framework-sideloading
    :alt: Build Status

.. image:: https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading
    :alt: Code Coverage

.. image:: https://readthedocs.org/projects/drf-sideloading/badge/?version=latest
    :target: http://drf-sideloading.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/pypi/dm/drf-sideloading.svg?maxAge=3600
    :alt: PyPI Downloads
    :target: https://pypi.python.org/pypi/drf-sideloading

.. image:: https://img.shields.io/github/license/mashape/apistatus.svg?maxAge=2592000
    :alt: License is MIT
    :target: https://github.com/namespace-ee/drf-sideloading/blob/master/LICENSE

Extension for Django Rest Framework to enable simple sideloading

Documentation
-------------

The full documentation is at https://drf-sideloading.readthedocs.io.

Quickstart
----------

Install drf-sideloading::

    pip install drf-sideloading

Import Mixin `SideloadableRelationsMixin`:

.. code-block:: python

    from drf_sideloading.mixins import SideloadableRelationsMixin


Include mixin in view and define serializers dict ``sideloadable_relations`` as shown in examples

It is ``required`` to define and indicate primary relationship in ``sideloadable_relations`` dict

Example of using mixin in ViewSet

.. code-block:: python

    class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
        """
        A simple ViewSet for viewing and editing products.
        """
        queryset = Product.objects.all()
        serializer_class = ProductSerializer

        sideloadable_relations = {
            'products': {'primary': True, 'serializer': ProductSerializer},
            'categories': {'serializer': CategorySerializer, 'source': 'category', 'prefetch': ['category']},
            'suppliers': {'serializer': SupplierSerializer, 'source': 'supplier', 'prefetch': ['supplier']},
            'partners': {'serializer': PartnerSerializer, 'source': 'partners', 'prefetch': ['partners']}
    }



To test it out send ``GET`` request:

``GET /product/?sideload=categories,partners,suppliers``

Response looks like:

.. sourcecode:: json

    {
        "categories": [
            {
                "id": 1,
                ...
            }
        ],
        "partners": [
            {
                "id": 1,
                ...
            },
            {
                "id": 2,
                ...
            },
            {
                "id": 3,
                ...
            }
        ],
        "products": [
            {
                "id": 1,
                "name": "Product 1",
                "category": 1,
                "supplier": 1,
                "partner": [
                    1,
                    2,
                    3
                ]
            }
        ],
        "suppliers": [
            {
                "id": 1,
                ...
            }
        ]
    }




Example Project
-----------------------

    directory `example` includes example project
    you can setup and run int locally using following commands

::

    cd example
    sh scripts/devsetup.sh
    sh scripts/dev.sh


Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox


manually specify env

::

    export TOX_ENV=py36-django18-drf34
    tox -e $TOX_ENV



# TODO

* fix documentation
* improve coverage



Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
