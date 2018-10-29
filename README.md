[![Package Index](https://badge.fury.io/py/drf-sideloading.svg)](https://badge.fury.io/py/drf-sideloading)
[![Build Status](https://travis-ci.org/namespace-ee/django-rest-framework-sideloading.svg?branch=master)](https://travis-ci.org/namespace-ee/django-rest-framework-sideloading)
[![Code Coverage](https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading/branch/master/graph/badge.svg)](https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading)
[![Documentation Status](https://readthedocs.org/projects/drf-sideloading/badge/?version=latest)](http://drf-sideloading.readthedocs.io/en/latest/?badge=latest)
[![License is MIT](https://img.shields.io/github/license/mashape/apistatus.svg?maxAge=2592000)](https://github.com/namespace-ee/drf-sideloading/blob/master/LICENSE)
[![Code style Black](https://img.shields.io/badge/code%20style-black-000000.svg?maxAge=2592000)](https://github.com/ambv/black)

# Django rest framework sideloading

DRF-sideloading is an extension to provide side-loading functionality of related resources. Side-loading allows related resources to be optionally included in a single API response minimizing requests to the API.

## Documentation

The full documentation is at https://drf-sideloading.readthedocs.io.

## Quickstart

1. Install drf-sideloading:

```shell
pip install drf-sideloading
```

2. Import `SideloadableRelationsMixin`:

```python
from drf_sideloading.mixins import SideloadableRelationsMixin
```

3. Configure sideloading
   Include mixin in view and define serializers dict `sideloadable_relations` as shown in examples.
   It is **required** to define and indicate a **primary** relationship in **sideloadable_relations** dict.

Example of using mixin in ViewSet:

```python
class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    sideloadable_relations = {
        'products': {'primary': True, 'serializer': ProductSerializer},
        'categories': {'serializer': CategorySerializer, 'source': 'category', 'prefetch': 'category'},
        'suppliers': {'serializer': SupplierSerializer, 'source': 'supplier', 'prefetch': 'supplier'},
        'partners': {'serializer': PartnerSerializer, 'source': 'partners', 'prefetch': 'partners'}
    }
```

Request::

    GET /product/?sideload=categories,partners,suppliers

Response::

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

## Example Project

Directory `example` contains an example project using django rest framework sideloading library. You can set it up and run it locally using following commands:

```shell
cd example
sh scripts/devsetup.sh
sh scripts/dev.sh
```

## Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

#### Setup for contribution

```shell
source <YOURVIRTUALENV>/bin/activate
(myenv) $ pip install -r requirements_dev.txt
```

### Test with specific env

```shell
$ tox --listenvs
py27-django18-drf34
py27-django19-drf34
# ...
$ tox -e py27-django19-drf34
```

Test coverage

```shell
$ make coverage
```

Use [pyenv](https://github.com/pyenv/pyenv) for testing using different python versions locally.

## License

## Credits

- [Demur Nodia](https://github.com/demonno)
- [Tõnis Väin](https://github.com/tonisvain)
- [Madis Väin](https://github.com/madisvain)
- [Lenno Nagel](https://github.com/lnagel)
