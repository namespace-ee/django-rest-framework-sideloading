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

Import Mixin `SideloadableRelationsMixin`:

.. code-block:: python

    from drf_sideloading.mixins import SideloadableRelationsMixin

Include mixin in view, define serializers dict `sideloadable_relations` and `base_model_name`

.. code-block:: python

    class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
        """
        A simple ViewSet for viewing and editing products.
        """
        queryset = Product.objects.all()
        serializer_class = ProductSerializer

        base_model_name = 'product'

        sideloadable_relations = {
            'product': ProductSerializer,
            'category': CategorySerializer,
            'supplier': SupplierSerializer,
            'partner': PartnerSerializer
        }


Add extra parameter and define comma separated relations:

`GET` `http://example.com/product/?sideload=category,partner,supplier`


Features
--------

* TODO
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
