#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_drf-sideloading
------------

Tests for `drf-sideloading` models api.
"""

from django.test import TestCase

from django.core.urlresolvers import reverse
from rest_framework import status

from tests.models import Category, Supplier, Product


class TestDrfSideloading(TestCase):

    def setUp(self):
        category = Category.objects.create(name='Category')
        supplier = Supplier.objects.create(name='Supplier')
        Product.objects.create(name="Product", category=category, supplier=supplier)

    def test_product_list(self):
        response = self.client.get(reverse('product-list'), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual('Product', response.data[0]['name'])

    def test_sideloading_product_list(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'category,supplier'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['category', 'supplier', 'product']

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

    def test_sideloading_category_product_list(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'category'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['category', 'product']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

    def test_sideloading_supplier_product_list(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'supplier'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['supplier', 'product']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))




