#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_drf-sideloading
------------

Tests for `drf-sideloading` models api.
"""

from django.core.urlresolvers import reverse
from django.test import TestCase
from rest_framework import status

from tests.models import Category, Supplier, Product, Partner
from tests.serializers import ProductSerializer, CategorySerializer, SupplierSerializer, PartnerSerializer
from tests.viewsets import ProductViewSet, CategoryViewSet


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

        product = Product.objects.create(name="Product", category=category, supplier=supplier)
        product.partners.add(partner1)
        product.partners.add(partner2)
        product.save()


class GeneralTestMixin(object):
    """Test general purpose without requesting sideloading enabled

    Check that drf-sideloading mixin doesn't break anything"""

    def test_product_list(self):
        response = self.client.get(reverse('product-list'), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual('Product', response.data[0]['name'])

    def test_category_list(self):
        response = self.client.get(reverse('category-list'), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual('Category', response.data[0]['name'])


class ProductSideloadTestCase(GeneralTestMixin, BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ProductSideloadTestCase, cls).setUpClass()

        sideloadable_relations = {
            'products': {'primary': True, 'serializer': ProductSerializer},
            'categories': {'serializer': CategorySerializer, 'source': 'category', 'prefetch': 'category'},
            'suppliers': {'serializer': SupplierSerializer, 'source': 'supplier', 'prefetch': 'supplier'},
            'partners': {'serializer': PartnerSerializer, 'source': 'partners', 'prefetch': 'partners'}
        }
        ProductViewSet.sideloadable_relations = sideloadable_relations

    def test_sideloading_product_list(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(reverse('product-list'), {'sideload': 'categories,suppliers,partners'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'categories', 'suppliers', 'partners']

        self.assertEqual(4, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_category_product_list(self):
        """sideload category"""
        response = self.client.get(reverse('product-list'), {'sideload': 'categories'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'categories']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_supplier_product_list(self):
        """sideload supplier"""
        response = self.client.get(reverse('product-list'), {'sideload': 'suppliers'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'suppliers']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_partner_product_list(self):
        """sideload partner"""
        response = self.client.get(reverse('product-list'), {'sideload': 'partners'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'partners']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    # negative test cases
    def test_sideloading_empty(self):
        response = self.client.get(reverse('product-list'), {'sideload': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['id', 'name', 'category', 'supplier', 'partners']
        product_list = response.data
        self.assertEqual(1, len(product_list))
        product = product_list[0]
        self.assertEqual(expected_relation_names, list(product.keys()))

    def test_sideloading_unexisting_relation(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'unexisting'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['id', 'name', 'category', 'supplier', 'partners']
        product_list = response.data
        self.assertEqual(1, len(product_list))
        product = product_list[0]
        self.assertEqual(expected_relation_names, list(product.keys()))

    def test_sideloading_supplier_unexisting_mixed_existing_relation(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'unexisting,suppliers'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'suppliers']

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_supplier_unexisting_mixed_existing_relation_middle(self):
        response = self.client.get(reverse('product-list'), {'sideload': 'categories,unexisting,suppliers'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'categories', 'suppliers']

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_supplier_wrongly_formed_quey(self):
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


class CategorySideloadTestCase(GeneralTestMixin, BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(CategorySideloadTestCase, cls).setUpClass()

        sideloadable_relations = {
            'categories': {'primary': True, 'serializer': CategorySerializer},
            'products': {'serializer': ProductSerializer, 'source': 'products', 'prefetch': 'products'},
            'suppliers': {'serializer': SupplierSerializer, 'source': 'products__supplier', 'prefetch': 'products__supplier'},
            'partners': {'serializer': PartnerSerializer, 'source': 'products__partners', 'prefetch': 'products__partners'}
        }

        CategoryViewSet.sideloadable_relations = sideloadable_relations
        CategoryViewSet.query_param_name = 's'

    def test_sideloading_category_list(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(reverse('category-list'), {'s': 'products,suppliers,partners'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ['products', 'categories', 'suppliers', 'partners']

        self.assertEqual(4, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))


# incorrect use of API
class TestDrfSideloadingNoRelationsDefined(BaseTestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoRelationsDefined, cls).setUpClass()

        sideloadable_relations = {
            'product': {'serializer': ProductSerializer},
            'category': {'serializer': CategorySerializer},
            'supplier': {'serializer': SupplierSerializer},
            'partners': {'serializer': PartnerSerializer}
        }

        ProductViewSet.sideloadable_relations = sideloadable_relations

    def test_correct_exception_raised(self):
        with self.assertRaises(Exception) as cm:
            self.client.get(reverse('product-list'), format='json')

        expected_error_message = "It is required to define primary model {'primary': True, ...}"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


# incorrect use of API
class TestDrfSideloadingRelationsNotDictionaries(BaseTestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingRelationsNotDictionaries, cls).setUpClass()

        sideloadable_relations = {
            'product': ProductSerializer,
            'category': CategorySerializer,
            'supplier': SupplierSerializer,
            'partners': PartnerSerializer
        }

        ProductViewSet.sideloadable_relations = sideloadable_relations

    def test_correct_exception_raised(self):
        with self.assertRaises(Exception) as cm:
            self.client.get(reverse('product-list'), format='json')

        expected_error_message = "All sideloadable relations must be defined as dictionaries"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingNoPrimaryIndicated(BaseTestCase):
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


# TODO:
# class TestDrfSideloadingNegative(BaseTestCase, SideloadRelatedTestMixin, GeneralTestMixin):
#     """ Test Cases of incorrect use of API """
#
#     @classmethod
#     @unittest.skip('Pending tests')
#     def setUpClass(cls):
#         super(TestDrfSideloadingNegative, cls).setUpClass()
#         # Define just serializer without indicate primary model in dict
#         sideloadable_relations = {
#             'product': {'serializer': ProductSerializer},
#             'category': {'serializer': CategorySerializer},
#             'supplier': {'serializer': SupplierSerializer},
#             'partner': {'serializer': PartnerSerializer}
#         }
#         ProductViewSet.sideloadable_relations = sideloadable_relations
#
#         # used for assertion
#         cls.primary_relation_name = 'self'


# TODO:
# class TestDrfSideloadingNoRelation(BaseTestCase, SideloadRelatedTestMixin, GeneralTestMixin):
#     """ Test Cases of incorrect use of API """
#
#     @classmethod
#     @unittest.skip('Pending tests')
#     def setUpClass(cls):
#         super(TestDrfSideloadingNoRelation, cls).setUpClass()
#         # Not define sideloadable_relations at all
#         sideloadable_relations = None
#         ProductViewSet.sideloadable_relations = sideloadable_relations
