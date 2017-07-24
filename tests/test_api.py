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

    # negative test cases
    def test_sideloading_supplier_empty(self):
        response = self.client.get(reverse('product-list'), {'sideload': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['id', 'name', 'category', 'supplier', 'partner']
        self.assertEqual(expected_loads, response.data[0].keys())

    def test_sideloading_supplier_unexisting_relation(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'unexisting'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['id', 'name', 'category', 'supplier', 'partner']
        self.assertEqual(expected_loads, response.data[0].keys())

    def test_sideloading_supplier_unexisting_mixed_existing_relation(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'unexisting,supplier'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['supplier', 'product']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

    def test_sideloading_supplier_unexisting_mixed_existing_relation_middle(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'category,unexisting,supplier'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['category', 'supplier', 'product']

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

    def test_sideloading_supplier_wrongly_forrmed_quey(self):
        response = self.client.get(reverse('product-list'),
                                   {'sideload': ',,@,123,category,123,.unexisting,123,,,,supplier,!@'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['category', 'supplier', 'product']

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))
