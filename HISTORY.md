# Changelog

## 2.1.0 (2024-01-26)

- Support for Django 4
  - Django supported versions `4.0 -> 4.2`
  - Python supported versions `3.10 -> 3.11`
  - Django-rest-framework supported versions. `3.13 -> 3.14`
- Fix issue with prefetch ordering

## 2.0.1 (2021-12-16)

- Ensure that only allowed methods are sideloaded

## 2.0.0 (2021-12-10)

Major refactoring to allow for multi source fields.

- Add support for multi source fields
- Add support for detail view sideloading
- Dropped formless BrowsableAPIRenderer enforcement
- Raises error in case invalid fields are requested for sideloading

## 1.4.2 (2021-04-12)

- Add support for lists in filter_related_objects

## 1.4.1 (2021-04-09)

- Fix sideloadable prefetches

## 1.4.0 (2021-04-07)

- Python supported versions `3.6 -> 3.9`
- Django supported versions `2.2`, `3.1`, `3.2`
- Django-rest-framework supported versions. `3.9 -> 3.12`

## 1.3.1 (2021-04-07)

Added support for `django.db.models.Prefetch`

## 1.3.0 (2019-04-23)

Fix empty related fields sideloading bug

- Support for Django 2.2

## 1.2.0 (2018-10-29)

Completely refactored sideloading configuration via a custom serializer.

- Support for Django 2.1
- Support for Django-rest-framework 3.9

## 0.1.10 (2017-07-20)

- Support for Django 2.0

## 0.1.8 (2017-07-20)

- change sideloadable_relations dict
- always required to define 'serializer'
- key is referenced to url and serialized in as rendered json
- add `source` which specifies original model field name

## 0.1.0 (2017-07-20)

- First release on PyPI.
