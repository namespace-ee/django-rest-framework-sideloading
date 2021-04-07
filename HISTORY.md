# Changelog

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
