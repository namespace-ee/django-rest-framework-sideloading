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

Extention for Django Rest Framework to enable simple sidloading

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

Common Example of using library in ViewSet

.. code-block:: python

    class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
        """
        A simple ViewSet for viewing and editing products.
        """
        queryset = Product.objects.all()
        serializer_class = ProductSerializer

        sideloadable_relations = {
            'product': {'primary':True, 'serializer': ProductSerializer},
            'category': {'serializer': CategorySerializer, 'name': 'categories'},
            'supplier': SupplierSerializer,
            'partner': PartnerSerializer
        }



To test it out send ``GET`` request:

``GET /product/?sideload=category,partner,supplier``

Response looks like:

.. sourcecode:: json

    {
        "category": [
            {
                "id": 1,
                ...
            }
        ],
        "partner": [
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
        "product": [
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
        "supplier": [
            {
                "id": 1,
                ...
            }
        ]
    }



Features
--------

``sideloadable_relations`` dict values supports following types
    * ``serializers.Serializer`` or subclass
    * ``dictionary`` with following keys
        * ``primary`` - indicates primary model
        * ``serializer`` - serializer class
        * ``name`` - override name of the sideloaded relation


note: invalid or unexisting relation names will be ignored and only valid relation name matches will be used

TODO

* fix documentation
* improve coverage
* python3 support


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
