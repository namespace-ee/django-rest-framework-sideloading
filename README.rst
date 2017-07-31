=============================
drf-sideloading
=============================

.. image:: https://badge.fury.io/py/drf-sideloading.svg
    :target: https://badge.fury.io/py/drf-sideloading
    :alt: Package Index

.. image:: https://travis-ci.org/namespace-ee/drf-sideloading.svg?branch=master
    :target: https://travis-ci.org/namespace-ee/drf-sideloading
    :alt: Build Status

.. image:: https://codecov.io/gh/namespace-ee/drf-sideloading/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/namespace-ee/drf-sideloading
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


Include mixin in view, define serializers dict `sideloadable_relations` and `base_model_name`

Defining primary relationship is optional if defined defaults will be overrided
In below case we define primary relationship along with side ones.
By adding `'product': {'primary':True},` in `sideloadable_relations` dict we

.. code-block:: python

    class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
        """
        A simple ViewSet for viewing and editing products.
        """
        queryset = Product.objects.all()
        serializer_class = ProductSerializer

        sideloadable_relations = {
            'product': {'primary':True},
            'category': CategorySerializer,
            'supplier': SupplierSerializer,
            'partner': PartnerSerializer
        }



Add extra parameter and define comma separated relations:

``GET /product/?sideload=category,partner,supplier``


.. sourcecode:: json

    {
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
        "categories": [
            {
                "id": 1,
                ...
            }
        ],
        "suppliers": [
            {
                "id": 1,
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
        ]
    }


Another use case

.. code-block:: python

    sideloadable_relations = {
        'product': {'primary': True, 'serializer': ProductSerializer, 'name': 'products'},
        'category': {'serializer': CategorySerializer, 'name': 'categories'},
        'supplier': SupplierSerializer,
        'partner': PartnerSerializer
    }




Features
--------

`sideloadable_relations` dict values supports following types
    *  `serializers.Serializer` or subclass
    * `dictionary` with following keys
        * `primary` - to indicate primary model
        * `serializer` - serializer class
        * `name` - to override name of the sideloaded relation


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
