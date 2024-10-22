[![Package Index](https://badge.fury.io/py/drf-sideloading.svg)](https://badge.fury.io/py/drf-sideloading)
[![Build Status](https://travis-ci.org/namespace-ee/django-rest-framework-sideloading.svg?branch=master)](https://travis-ci.org/namespace-ee/django-rest-framework-sideloading)
[![Code Coverage](https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading/branch/master/graph/badge.svg)](https://codecov.io/gh/namespace-ee/django-rest-framework-sideloading)
[![License is MIT](https://img.shields.io/github/license/mashape/apistatus.svg?maxAge=2592000)](https://github.com/namespace-ee/drf-sideloading/blob/master/LICENSE)
[![Code style Black](https://img.shields.io/badge/code%20style-black-000000.svg?maxAge=2592000)](https://github.com/ambv/black)

:warning: Note that there are major API changes since version 0.1.1 that have to be taken into account when upgrading!

:warning: Python 2 and Django 1.11 are no longer supported from version 1.4.0!

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

3. Write your SideLoadableSerializer:
   
   You need to define the **primary** serializer in the Meta data and can define prefetching rules. 
   Also notice the **many=True** on the sideloadable relationships.

    ```python
    from drf_sideloading.serializers import SideLoadableSerializer
    
    class ProductSideloadableSerializer(SideLoadableSerializer):
        products = ProductSerializer(many=True)
        categories = CategorySerializer(source="category", many=True)
        primary_suppliers = SupplierSerializer(source="primary_supplier", many=True)
        secondary_suppliers = SupplierSerializer(many=True)
        suppliers = SupplierSerializer(many=True)
        partners = PartnerSerializer(many=True)
    
        class Meta:
            primary = "products"
            prefetches = {
                "categories": "category",
                "primary_suppliers": "primary_supplier",
                "secondary_suppliers": "secondary_suppliers",
                "suppliers": {
                    "primary_suppliers": "primary_supplier",
                    "secondary_suppliers": "secondary_suppliers",
                },
                "partners": "partners",
            }
    ```
   
4. Prefetches

   For fields where the source is provided or where the source matches the field name, prefetches are not strictly required

   Multiple prefetches can be added to a single sideloadable field, but when using Prefetch object check that they don't clash with prefetches made in the get_queryset() method
   ```python
   from django.db.models import Prefetch

   prefetches = {
       "categories": "category",
       "primary_suppliers": ["primary_supplier", "primary_supplier__some_related_object"],
       "secondary_suppliers": Prefetch(
           lookup="secondary_suppliers", 
           queryset=Supplier.objects.prefetch_related("some_related_object")
       ),
       "partners": Prefetch(
           lookup="partners", 
           queryset=Partner.objects.select_related("some_related_object")
       )
   }
   ```

   Multiple sources can be added to a field using a dict. 
   Each key is a source_key that can be used to filter what sources should be sideloaded.
   The values set the source and prefetches for this source.
   
   Note that this prefetch reuses `primary_supplier` and `secondary_suppliers` if suppliers and primary_supplier or secondary_suppliers are sideloaded
   ```python
   prefetches = {
       "primary_suppliers": "primary_supplier",
       "secondary_suppliers": "secondary_suppliers",
       "suppliers": {
           "primary_suppliers": "primary_supplier",
           "secondary_suppliers": "secondary_suppliers"
       }
   }
   ```

   Usage of Prefetch() objects is supported.
   Prefetch() objects can be used to filter a subset of some relations or just to prefetch or select complicated related objects
   In case there are prefetch conflicts, `to_attr` can be set but be aware that this prefetch will now be a duplicate of similar prefetches.
   prefetch conflicts can also come from prefetched made in the ViewSet.get_queryset() method.
   
   Note that this prefetch noes not reuse `primary_supplier` and `secondary_suppliers` if **suppliers** and **primary_supplier** or **secondary_suppliers** are sideloaded at the same time.
   ```python
   from django.db.models import Prefetch
   
   prefetches = {
       "categories": "category",
       "primary_suppliers": "primary_supplier",
       "secondary_suppliers": "secondary_suppliers",
       "suppliers": {
           "primary_suppliers": Prefetch(
               lookup="secondary_suppliers", 
               queryset=Supplier.objects.select_related("some_related_object"), 
               to_attr="secondary_suppliers_with_preselected_relation"
           ),
           "secondary_suppliers": Prefetch(
               lookup="secondary_suppliers", 
               queryset=Supplier.objects.filter(created_at__gt=pendulum.now().subtract(days=10)).order_by("created_at"), 
               to_attr="latest_secondary_suppliers"
           )
       },
   }
   ```

5. Configure sideloading in ViewSet:
   
   Include **SideloadableRelationsMixin** mixin in ViewSet and define **sideloading_serializer_class** as shown in example below. 
   Everything else stays just like a regular ViewSet.
   Since version 2.0.0 there are 3 new methods that allow to overwrite the serializer used based on the request version for example
   Since version 2.1.0 an additional method was added that allow to add request dependent filters to sideloaded relations

    ```python
    from drf_sideloading.mixins import SideloadableRelationsMixin
    
    class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
        """
        A simple ViewSet for viewing and editing products.
        """
    
        queryset = Product.objects.all()
        serializer_class = ProductSerializer
        sideloading_serializer_class = ProductSideloadableSerializer
   
        def get_queryset(self):
            # Add prefetches for the viewset as normal 
            return super().get_queryset().prefetch_related("created_by")
   
        def get_sideloading_serializer_class(self, request=None):
            # use a different sideloadable serializer for older version 
            if self.request.version < "1.0.0":
                return OldProductSideloadableSerializer
            return super().get_sideloading_serializer_class(request=request)
   
        def get_sideloading_serializer(self, *args, **kwargs):
            # if modifications are required to the serializer initialization this method can be used.
            return super().get_sideloading_serializer(*args, **kwargs)
   
        def get_sideloading_serializer_context(self):
            # Extra context provided to the serializer class.
            return {"request": self.request, "format": self.format_kwarg, "view": self}
      
        def add_sideloading_prefetch_filter(self, source, queryset, request):
             # 
            if source == "model1__relation1":
                return queryset.filter(is_active=True), True
            if hasattr(queryset, "readable"):
                return queryset.readable(user=request.user), True
            return queryset, False
    ```

6. Enjoy your API with sideloading support

   Example request and response when fetching all possible values
    ```http
    GET /api/products/?sideload=categories,partners,primary_suppliers,secondary_suppliers,suppliers,products
    ```

    ```json
    {
      "products": [
        {
          "id": 1,
          "name": "Product 1",
          "category": 1,
          "primary_supplier": 1,
          "secondary_suppliers": [2, 3],
          "partners": [1, 2, 3]
        }
      ],
      "categories": [
        {
          "id": 1,
          "name": "Category1"
        }
      ],
      "primary_suppliers": [
        {
          "id": 1,
          "name": "Supplier1"
        }
      ],
      "secondary_suppliers": [
        {
          "id": 2,
          "name": "Supplier2"
        },
        {
          "id": 3,
          "name": "Supplier3"
        }
      ],
      "suppliers": [
        {
          "id": 1,
          "name": "Supplier1"
        },
        {
          "id": 2,
          "name": "Supplier2"
        },
        {
          "id": 3,
          "name": "Supplier3"
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
   
   The user can also select what sources to load to Multi source fields. 
   Leaving the selections empty or omitting the brackets will load all the prefetched sources.
   
   Example:

    ```http
    GET /api/products/?sideload=suppliers[primary_suppliers]
    ```
   ```json
    {
      "products": [
        {
          "id": 1,
          "name": "Product 1",
          "category": 1,
          "primary_supplier": 1,
          "secondary_suppliers": [2, 3],
          "partners": [1, 2, 3]
        }
      ],
      "suppliers": [
        {
          "id": 1,
          "name": "Supplier1"
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
