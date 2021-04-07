[![Package Index](https://badge.fury.io/py/drf-sideloading.svg)](https://badge.fury.io/py/drf-sideloading)
[![Build Status](https://travis-ci.org/namespace-ee/django-rest-framework-sideloading.svg?branch=master)](https://travis-ci.org/namespace-ee/django-rest-framework-sideloading)
[![Code Coverage](https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading/branch/master/graph/badge.svg)](https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading)
[![Documentation Status](https://readthedocs.org/projects/drf-sideloading/badge/?version=latest)](http://drf-sideloading.readthedocs.io/en/latest/?badge=latest)
[![License is MIT](https://img.shields.io/github/license/mashape/apistatus.svg?maxAge=2592000)](https://github.com/namespace-ee/drf-sideloading/blob/master/LICENSE)
[![Code style Black](https://img.shields.io/badge/code%20style-black-000000.svg?maxAge=2592000)](https://github.com/ambv/black)

:warning: Note that there are major API changes since version 0.1.1 that have to be taken into account when upgrading!

# Django rest framework sideloading

DRF-sideloading is an extension to provide side-loading functionality of related resources. Side-loading allows related resources to be optionally included in a single API response minimizing requests to the API.

## Quickstart

1. Install drf-sideloading:

```shell
pip install drf-sideloading
```

2. Import `SideloadableRelationsMixin`:

```python
from drf_sideloading.mixins import SideloadableRelationsMixin
```

3. Write your SideLoadableSerializer
   You need to define the **primary** serializer in the Meta data and can define prefetching rules. Also notice the **many=True** on the sideloadable relationships.

```python
from drf_sideloading.serializers import SideLoadableSerializer

class ProductSideloadableSerializer(SideLoadableSerializer):
    products = ProductSerializer(many=True)
    categories = CategorySerializer(source="category", many=True)
    suppliers = SupplierSerializer(source="supplier", many=True)
    partners = PartnerSerializer(many=True)

    class Meta:
        primary = "products"
        prefetches = {
            "categories": "category",
            "suppliers": "supplier",
            "partners": "partners",
        }
```

4. Configure sideloading
   Include **SideloadableRelationsMixin** mixin in ViewSet and define **sideloading_serializer_class** as shown in example below. Evrything else stays just like a regular ViewSet

```python
from drf_sideloading.mixins import SideloadableRelationsMixin

class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloading_serializer_class = ProductSideloadableSerializer
```

5. Enjoy your API with sideloading support

```http
GET /api/products/?sideload=categories,partners,suppliers,products
```

```json
{
  "products": [
    {
      "id": 1,
      "name": "Product 1",
      "category": 1,
      "supplier": 1,
      "partners": [1, 2, 3]
    }
  ],
  "categories": [
    {
      "id": 1,
      "name": "Category1"
    }
  ],
  "suppliers": [
    {
      "id": 1,
      "name": "Supplier1"
    }
  ],
  "partners": [
    {
      "id": 1,
      "name": "Partner1"
    },
    {
      "id": 2,
      "name": "Partner1"
    },
    {
      "id": 3,
      "name": "Partner3"
    }
  ]
}
```

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

### Test

```shell
$ make test
```

#### Run tests with environment matrix

```shell
$ make tox
```

#### Run tests with specific environment

```shell
$ tox --listenvs
py37-django22-drf39
py38-django31-drf311
py39-django32-drf312
# ...
$ tox -e py39-django32-drf312
```

#### Test coverage

```shell
$ make coverage
```

Use [pyenv](https://github.com/pyenv/pyenv) for testing using different python versions locally.

## License

[MIT](https://github.com/namespace-ee/drf-sideloading/blob/master/LICENSE)

## Credits

- [Demur Nodia](https://github.com/demonno)
- [Tõnis Väin](https://github.com/tonisvain)
- [Madis Väin](https://github.com/madisvain)
- [Lenno Nagel](https://github.com/lnagel)
