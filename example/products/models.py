# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)


class Supplier(models.Model):
    name = models.CharField(max_length=255)


class Partner(models.Model):
    name = models.CharField(max_length=255)


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category)
    supplier = models.ForeignKey(Supplier)
    partner = models.ManyToManyField(Partner)
