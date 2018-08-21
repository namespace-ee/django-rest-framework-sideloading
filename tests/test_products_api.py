#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from drf_sideloading.serializers import SideLoadableSerializer
from tests import DJANGO_20

from django.test import TestCase
from rest_framework import status

from tests.models import Category, Supplier, Product, Partner
from tests.serializers import ProductSerializer, CategorySerializer, SupplierSerializer, PartnerSerializer
from tests.viewsets import ProductViewSet, CategoryViewSet

if DJANGO_20:
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse


class BaseTestCase(TestCase):
    """Minimum common model setups"""

    @classmethod
    def setUpClass(cls):
        super(BaseTestCase, cls).setUpClass()

    def setUp(self):
        category = Category.objects.create(name='Category')
        supplier = Supplier.objects.create(name='Supplier')
        partner1 = Partner.objects.create(name='Partner1')
        partner2 = Partner.objects.create(name='Partner2')

        product = Product.objects.create(name='Product', category=category, supplier=supplier)
        product.partners.add(partner1)
        product.partners.add(partner2)
        product.save()


###################################
# Different Correct usages of API #
###################################
class ProductSideloadTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ProductSideloadTestCase, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer()
            categories = CategorySerializer(source='category')
            suppliers = SupplierSerializer(source='supplier')
            partners = PartnerSerializer(source='partners')

            class Meta:
                primary = 'products'
                prefetches = {
                    'categories': 'category',
                    'suppliers': 'supplier',
                    'partners': 'partners',
                }

        ProductViewSet.sideloadable_serializer_class = ProductSideloadableSerializer

    def test_list(self):
        response = self.client.get(reverse('product-list'), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual('Product', response.data[0]['name'])

    def test_list_sideloading(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(reverse('product-list'), {'sideload': 'categories,suppliers,partners'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'categories', 'suppliers', 'partners']

        self.assertEqual(4, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    # all negative test cases below only here
    def test_sideload_param_empty_string(self):
        response = self.client.get(reverse('product-list'), {'sideload': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual('Product', response.data[0]['name'])

    def test_sideload_param_nonexistent_relation(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'nonexistent'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual('Product', response.data[0]['name'])

    def test_sideload_param_nonexistent_mixed_existing_relation(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'nonexistent,suppliers'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'suppliers']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_param_wrongly_formed_quey(self):
        response = self.client.get(reverse('product-list'),
                                   {'sideload': ',,@,123,categories,123,.unexisting,123,,,,suppliers,!@'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'categories', 'suppliers']

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_partner_product_use_primary_list(self):
        """use primary model as a sideload relation request should not fail"""
        response = self.client.get(reverse('product-list'), {'sideload': 'partners,products'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'partners']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))


###########################################################
# Incorrect definitions sideloadable_relations in ViewSet #
###########################################################
class TestDrfSideloadingNoPrimaryDefined(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoPrimaryDefined, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer()
            categories = CategorySerializer()
            suppliers = SupplierSerializer()
            partners = PartnerSerializer()

        ProductViewSet.sideloadable_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(Exception) as cm:
            self.client.get(reverse('product-list'), format='json')

        expected_error_message = "It is required to define primary model {'primary': True, ...}"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingRelationsNotDictionaries(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingRelationsNotDictionaries, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer()
            categories = CategorySerializer()
            suppliers = SupplierSerializer()
            partners = PartnerSerializer()

        ProductViewSet.sideloadable_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(Exception) as cm:
            self.client.get(reverse('product-list'), format='json')

        expected_error_message = "All sideloadable relations must be defined as dictionaries"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingNoPrimaryIndicated(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoPrimaryIndicated, cls).setUpClass()
        delattr(ProductViewSet, "sideloadable_relations")

    def test_correct_exception_raised(self):
        with self.assertRaises(Exception) as cm:
            self.client.get(reverse('product-list'), format='json')

        expected_error_message = "define `sideloadable_relations` class variable, while using `SideloadableRelationsMixin`"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


##############################
# TODO Move to separate file #
##############################
class CategorySideloadTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(CategorySideloadTestCase, cls).setUpClass()

        class CategorySideloadableSerializer(SideLoadableSerializer):
            categories = CategorySerializer()
            products = ProductSerializer(source='products')
            suppliers = SupplierSerializer(source='products__supplier')
            partners = PartnerSerializer(source='products__partners')

            class Meta:
                primary = 'categories'
                prefetches = {
                    'products': 'products',
                    'suppliers': 'products__supplier',
                    'partners': 'products__partners',
                }

        ProductViewSet.sideloadable_serializer_class = CategorySideloadableSerializer
        CategoryViewSet.query_param_name = 's'

    def test_sideloading_category_list(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(reverse('category-list'), {'s': 'products,suppliers,partners'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'categories', 'suppliers', 'partners']

        self.assertEqual(4, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))
