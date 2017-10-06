#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_drf-sideloading
------------

Tests for `drf-sideloading` models api.
"""
import unittest

from django.core.urlresolvers import reverse
from django.test import TestCase
from rest_framework import status

from tests.models import Category, Supplier, Product, Partner
from tests.serializers import ProductSerializer, CategorySerializer, SupplierSerializer, PartnerSerializer
from tests.viewsets import ProductViewSet


class BaseTestCase(TestCase):
    """Do minimum common setups for testcases which can be reused"""
    @classmethod
    def setUpClass(cls):
        super(BaseTestCase, cls).setUpClass()

    def setUp(self):
        category = Category.objects.create(name='Category')
        supplier = Supplier.objects.create(name='Supplier')
        partner1 = Partner.objects.create(name='Partner1')
        partner2 = Partner.objects.create(name='Partner2')

        product = Product.objects.create(name="Product", category=category, supplier=supplier)
        product.partner.add(partner1)
        product.partner.add(partner2)
        product.save()


class GeneralTestMixin(object):
    """Tests for general purpose without requesting sideloading enabled

    Check that drf-sideloading mixin doesn't break anything"""

    def test_product_list(self):
        response = self.client.get(reverse('product-list'), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual('Product', response.data[0]['name'])


class SideloadRelatedTestMixin(object):
    """Sideloading enabled testcases

    Can be reused by defining different configurations bforehand"""

    def test_sideloading_product_list(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'category,supplier'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = [self.category_relation_name, 'supplier'] + [self.primary_model_name]

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

    def test_sideloading_category_product_list(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'category'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = [self.category_relation_name, self.primary_model_name]

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

    def test_sideloading_supplier_product_list(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'supplier'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['supplier'] + [self.primary_model_name]

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

    def test_sideloading_partner_product_list(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'partner'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['partner'] + [self.primary_model_name]

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

        self.assertEqual(2, len(response.data['partner']))


class TestDrfSideloadingNamed(BaseTestCase, SideloadRelatedTestMixin, GeneralTestMixin):
    """Test sideloading by specifying different names to be as keys"""
    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNamed, cls).setUpClass()

        # used for assertion
        cls.primary_model_name = 'product'
        cls.category_relation_name = 'categories'

        sideloadable_relations = {
            'product': {'primary': True, 'serializer': ProductSerializer},
            'category': {'serializer': CategorySerializer, 'name': cls.category_relation_name},
            'supplier': SupplierSerializer,
            'partner': PartnerSerializer
        }
        ProductViewSet.sideloadable_relations = sideloadable_relations


class TestDrfSideloading(BaseTestCase, SideloadRelatedTestMixin, GeneralTestMixin):
    """Test most common usecase of the library"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloading, cls).setUpClass()
        sideloadable_relations = {
            'product': {'primary': True, 'serializer': ProductSerializer},
            'category': CategorySerializer,
            'supplier': SupplierSerializer,
            'partner': PartnerSerializer
        }
        ProductViewSet.sideloadable_relations = sideloadable_relations

        cls.primary_model_name = 'product'
        cls.category_relation_name = 'category'

    # negative test cases
    def test_sideloading_supplier_empty(self):
        response = self.client.get(reverse('product-list'), {'sideload': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['id', 'name', 'category', 'supplier', 'partner']
        self.assertEqual(expected_loads, list(response.data[0].keys()))

    def test_sideloading_supplier_unexisting_relation(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'unexisting'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['id', 'name', 'category', 'supplier', 'partner']
        self.assertEqual(expected_loads, list(response.data[0].keys()))

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

    def test_sideloading_partner_product_use_primary_list(self):
        """using primary model as a sideload relation request should not fail"""
        response = self.client.get(reverse('product-list'), {'sideload': 'partner,product'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_loads = ['product', 'partner']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_loads), set(response.data))

        self.assertEqual(2, len(response.data['partner']))


# incorrect use of API
class TestDrfSideloadingNoRelationsDefined(BaseTestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoRelationsDefined, cls).setUpClass()
        delattr(ProductViewSet, "sideloadable_relations")

    def test_correct_exception_raised(self):
        with self.assertRaises(Exception) as cm:
            self.client.get(reverse('product-list'), format='json')

        expected_error_message = "define `sideloadable_relations` class variable, while using `SideloadableRelationsMixin`"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingNegative(BaseTestCase, SideloadRelatedTestMixin, GeneralTestMixin):
    """ Test Cases of incorrect use of API """

    @classmethod
    @unittest.skip('Pending tests')
    def setUpClass(cls):
        super(TestDrfSideloadingNegative, cls).setUpClass()
        # Define just serializer without indicate primary model in dict
        sideloadable_relations = {
            'product': ProductSerializer,
            'category': CategorySerializer,
            'supplier': SupplierSerializer,
            'partner': PartnerSerializer
        }
        ProductViewSet.sideloadable_relations = sideloadable_relations

        # used for assertion
        cls.primary_model_name = 'self'


class TestDrfSideloadingNoRelation(BaseTestCase, SideloadRelatedTestMixin, GeneralTestMixin):
    """ Test Cases of incorrect use of API """

    @classmethod
    @unittest.skip('Pending tests')
    def setUpClass(cls):
        super(TestDrfSideloadingNoRelation, cls).setUpClass()
        # Not define sideloadable_relations at all
        sideloadable_relations = None
        ProductViewSet.sideloadable_relations = sideloadable_relations
