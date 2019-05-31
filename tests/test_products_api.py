#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from rest_framework.permissions import BasePermission
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.settings import api_settings

from drf_sideloading.serializers import SideLoadableSerializer, SelectableDataSerializer
from tests import DJANGO_20

from django.test import TestCase
from rest_framework import status, serializers

from tests.models import Category, Supplier, Product, Partner
from tests.serializers import (
    ProductSerializer,
    CategorySerializer,
    SupplierSerializer,
    PartnerSerializer,
)
from tests.viewsets import ProductViewSet

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
        category = Category.objects.create(name="Category")
        supplier = Supplier.objects.create(name="Supplier")
        partner1 = Partner.objects.create(name="Partner1")
        partner2 = Partner.objects.create(name="Partner2")

        product = Product.objects.create(
            name="Product", category=category, supplier=supplier
        )
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

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_list(self):
        response = self.client.get(reverse("product-list"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual("Product", response.data[0]["name"])

    def test_list_sideloading(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(
            reverse("product-list"), {"sideload": "categories,suppliers,partners"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "categories", "suppliers", "partners"]

        self.assertEqual(4, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_list_partial_sideloading(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(
            reverse("product-list"), {"sideload": "suppliers,partners"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "suppliers", "partners"]

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    # all negative test cases below only here
    def test_sideload_param_empty_string(self):
        response = self.client.get(reverse("product-list"), {"sideload": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual("Product", response.data[0]["name"])

    def test_sideload_param_nonexistent_relation(self):
        response = self.client.get(reverse("product-list"), {"sideload": "nonexistent"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual("Product", response.data[0]["name"])

    def test_sideload_param_nonexistent_mixed_existing_relation(self):
        response = self.client.get(
            reverse("product-list"), {"sideload": "nonexistent,suppliers"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "suppliers"]

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_param_wrongly_formed_quey(self):
        response = self.client.get(
            reverse("product-list"),
            {"sideload": ",,@,123,categories,123,.unexisting,123,,,,suppliers,!@"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "categories", "suppliers"]

        self.assertEqual(3, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_partner_product_use_primary_list(self):
        """use primary model as a sideload relation request should not fail"""
        response = self.client.get(
            reverse("product-list"), {"sideload": "partners,products"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "partners"]

        self.assertEqual(2, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_flattening(self):
        response = self.client.get(
            reverse("product-list"),
            data={"flat": "true", "sideload": "suppliers"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        flat_product_data = response.data[0]
        # product data
        self.assertIsNotNone(flat_product_data.get("id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("name"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("category"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("partners"), flat_product_data)
        # supplier
        self.assertIsNone(flat_product_data.get("supplier"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("supplier__id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("supplier__name"), flat_product_data)

    def test_flattening_many_to_many(self):
        response = self.client.get(
            reverse("product-list"),
            data={"flat": "true", "sideload": "partners"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        flat_product_data = response.data[0]
        # product data
        self.assertIsNotNone(flat_product_data.get("id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("name"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("category"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("supplier"), flat_product_data)
        # partners
        self.assertIsNone(flat_product_data.get("partners"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("partners__0__id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("partners__0__name"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("partners__1__id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("partners__1__name"), flat_product_data)


class ProductSelectableDataTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(ProductSelectableDataTestCase, cls).setUpClass()

        class ProductSideloadableSerializer(SelectableDataSerializer, SideLoadableSerializer):
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

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_selected_fields_only(self):
        response = self.client.get(reverse("product-list"), data={"fields": "name,supplier"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual(2, len(response.data[0]))
        self.assertIsNotNone(response.data[0].get("name"))
        self.assertIsNotNone(response.data[0].get("supplier"))
        self.assertEqual("Product", response.data[0]["name"])

    def test_sideloading_with_selected_fields_only(self):
        response = self.client.get(
            reverse("product-list"),
            data={
                "sideload": "suppliers",
                "fields": "name,supplier__name"
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "suppliers"]
        self.assertEqual(set(expected_relation_names), set(response.data))

        self.assertEqual(1, len(response.data.get("products")))
        product_data = response.data.get("products")[0]
        self.assertEqual(1, len(product_data), response.data)
        self.assertIsNone(product_data.get("id"), response.data)
        self.assertIsNotNone(product_data.get("name"), response.data)
        self.assertIsNone(product_data.get("supplier"), response.data)

        self.assertEqual(1, len(response.data.get("suppliers")))
        supplier_data = response.data.get("suppliers")[0]
        self.assertEqual(1, len(supplier_data))
        self.assertIsNone(product_data.get("id"), response.data)
        self.assertIsNotNone(supplier_data.get("name"), response.data)

    def test_flat_sideloading_with_selected_fields_only(self):
        response = self.client.get(
            reverse("product-list"),
            data={
                "sideload": "suppliers",
                "fields": "name,supplier__name",
                "flat": "true",
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        flat_product_data = response.data[0]
        # product data
        self.assertIsNone(flat_product_data.get("id"), response.data)
        self.assertIsNotNone(flat_product_data.get("name"), response.data)
        self.assertIsNone(flat_product_data.get("category"), response.data)
        self.assertIsNone(flat_product_data.get("supplier"), response.data)
        self.assertIsNone(flat_product_data.get("partners"), response.data)
        # supplier
        self.assertIsNone(flat_product_data.get("supplier__id"), response.data)
        self.assertIsNotNone(flat_product_data.get("supplier__name"), response.data)

    def test_flat_with_selected_fields_only(self):
        response = self.client.get(
            reverse("product-list"),
            data={
                "fields": "name,supplier,supplier__name",
                "flat": "true",
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        flat_product_data = response.data[0]
        # product data
        self.assertIsNone(flat_product_data.get("id"), response.data)
        self.assertIsNotNone(flat_product_data.get("name"), response.data)
        self.assertIsNone(flat_product_data.get("category"), response.data)
        self.assertIsNotNone(flat_product_data.get("supplier"), response.data)
        self.assertIsNone(flat_product_data.get("partners"), response.data)
        # supplier
        self.assertIsNone(flat_product_data.get("supplier__id"), response.data)
        self.assertIsNone(flat_product_data.get("supplier__name"), response.data)

    def test_flattening_many_to_many_with_selected_fields(self):
        response = self.client.get(
            reverse("product-list"),
            data={"flat": "true", "sideload": "partners", "fields": "name,partners__name"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        flat_product_data = response.data[0]
        # product data
        self.assertIsNone(flat_product_data.get("id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("name"), flat_product_data)
        self.assertIsNone(flat_product_data.get("category"), flat_product_data)
        self.assertIsNone(flat_product_data.get("supplier"), flat_product_data)

        # partners
        self.assertIsNone(flat_product_data.get("partners"), flat_product_data)
        self.assertIsNone(flat_product_data.get("partners__0__id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("partners__0__name"), flat_product_data)
        self.assertIsNone(flat_product_data.get("partners__1__id"), flat_product_data)
        self.assertIsNotNone(flat_product_data.get("partners__1__name"), flat_product_data)


###################################
# Different Correct usages of API #
###################################
class CategorySideloadTestCase(BaseTestCase):
    def test_list(self):
        response = self.client.get(reverse("category-list"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(1, len(response.data))
        self.assertEqual("Category", response.data[0]["name"])

    def test_list_sideloading_with_reverse_relations_and_its_relations(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(
            reverse("category-list"), {"sideload": "products,suppliers,partners"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["categories", "products", "suppliers", "partners"]

        self.assertEqual(4, len(response.data))
        self.assertListEqual(expected_relation_names, list(response.data.keys()))

    def test_list_sideloading_with_reverse_relations_relations_without_the_reverse_relation_itself(
        self
    ):
        """Test sideloading for related items to products, that are related to the categories
        while the products list itself is not sideloaded"""
        response = self.client.get(
            reverse("category-list"), {"sideload": "suppliers,partners"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["categories", "suppliers", "partners"]

        self.assertEqual(3, len(response.data))
        self.assertListEqual(expected_relation_names, list(response.data.keys()))


######################################################################################
# Incorrect definitions sideloadable_relations in ViewSet and SideloadableSerializer #
######################################################################################
class TestDrfSideloadingNoMetaClassDefined(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoMetaClassDefined, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(AssertionError) as cm:
            self.client.get(
                reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                format="json",
            )

        expected_error_message = "Sideloadable serializer must have a Meta class defined with the 'primary' field name!"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingNoPrimaryDefined(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoPrimaryDefined, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                pass

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(AssertionError) as cm:
            self.client.get(
                reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                format="json",
            )

        expected_error_message = (
            "Sideloadable serializer must have a Meta attribute called primary!"
        )

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingRelationsNotListSerializers(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingRelationsNotListSerializers, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer()
            suppliers = SupplierSerializer()
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(AssertionError) as cm:
            self.client.get(
                reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
            )

        expected_error_message = (
            "SideLoadable field 'categories' must be set as many=True"
        )

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingInvalidPrimary(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrimary, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "other"

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(AssertionError) as cm:
            self.client.get(
                reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                format="json",
            )

        expected_error_message = "Sideloadable serializer Meta.primary must point to a field in the serializer!"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingInvalidPrefetchesType(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrefetchesType, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = (
                    ("categories", "category"),
                    ("suppliers", "supplier"),
                    ("partners", "partners"),
                )

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(AssertionError) as cm:
            self.client.get(
                reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                format="json",
            )

        expected_error_message = (
            "Sideloadable serializer Meta attribute 'prefetches' must be a dict."
        )

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingInvalidPrefetchesValuesType(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrefetchesValuesType, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    "partners": 123,
                }

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_correct_exception_raised(self):
        with self.assertRaises(RuntimeError) as cm:
            self.client.get(
                reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                format="json",
            )

        expected_error_message = "Sideloadable prefetch values must be presented either as a list or a string"

        raised_exception = cm.exception
        self.assertEqual(str(raised_exception), expected_error_message)


class TestDrfSideloadingValidPrefetches(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingValidPrefetches, cls).setUpClass()

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    "partners": None,
                }

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_sideloading_with_prefetches(self):
        self.client.get(
            reverse("product-list"),
            data={"sideload": "categories,suppliers,partners"},
            format="json",
        )

        response = self.client.get(
            reverse("product-list"), {"sideload": "categories,suppliers,partners"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "categories", "suppliers", "partners"]

        self.assertEqual(4, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))


class TestDrfSideloadingBrowsableApiPermissions(TestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingBrowsableApiPermissions, cls).setUpClass()

        class ProductPermission(BasePermission):
            def has_permission(self, request, view):
                """
                Return `True` if permission is granted, `False` otherwise.
                """
                return True

            def has_object_permission(self, request, view, obj):
                raise RuntimeError(
                    "This must not be called, when sideloadading is used!"
                )

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    "partners": None,
                }

        ProductViewSet.renderer_classes = (BrowsableAPIRenderer, JSONRenderer)
        ProductViewSet.permission_classes = (ProductPermission,)
        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    @classmethod
    def tearDownClass(cls):
        ProductViewSet.renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
        ProductViewSet.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
        super(TestDrfSideloadingBrowsableApiPermissions, cls).tearDownClass()

    def test_sideloading_does_not_render_forms_and_check_object_permissions(self):
        response = self.client.get(
            reverse("product-list"), data={"sideload": "categories,suppliers,partners"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "categories", "suppliers", "partners"]

        self.assertEqual(4, len(response.data))
        self.assertEqual(set(expected_relation_names), set(response.data))

    def test_sideloading_allow_post_without_sideloading(self):
        category = Category.objects.create(name="Category")
        supplier = Supplier.objects.create(name="Supplier")

        headers = {"HTTP_ACCEPT": "application/json"}
        response = self.client.post(
            reverse("product-list"),
            data={
                "name": "Random product",
                "category": category.id,
                "supplier": supplier.id,
                "partners": [],
            },
            **headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(isinstance(response.data, dict))

    def test_sideloading_allow_post_with_sideloading(self):
        category = Category.objects.create(name="Category")
        supplier = Supplier.objects.create(name="Supplier")

        headers = {"HTTP_ACCEPT": "application/json"}
        response = self.client.post(
            "{}{}".format(
                reverse("product-list"), "?sideload=categories,suppliers,partners"
            ),
            data={
                "name": "Random product",
                "category": category.id,
                "supplier": supplier.id,
                "partners": [],
            },
            **headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(isinstance(response.data, dict))


class ProductSideloadSameSourceDuplicationTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(ProductSideloadSameSourceDuplicationTestCase, cls).setUpClass()

        class OldCategorySerializer(serializers.ModelSerializer):
            old_name = serializers.CharField(source="name")

            class Meta:
                model = Category
                fields = ["old_name"]

        class ProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            old_categories = OldCategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {"category": "category", "old_categories": "category"}

        ProductViewSet.sideloading_serializer_class = ProductSideloadableSerializer

    def test_list_sideload_categories(self):
        response = self.client.get(reverse("product-list"), {"sideload": "categories"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "categories"]

        self.assertSetEqual(
            set(response.data.serializer.instance.keys()), {"products", "category"}
        )
        self.assertSetEqual(
            set(dict(response.data).keys()), set(expected_relation_names)
        )

    def test_list_sideload_old_categories(self):
        response = self.client.get(
            reverse("product-list"), {"sideload": "old_categories"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "old_categories"]

        self.assertSetEqual(
            set(response.data.serializer.instance.keys()), {"products", "category"}
        )
        self.assertSetEqual(
            set(dict(response.data).keys()), set(expected_relation_names)
        )

    def test_list_sideload_new_categories_and_old_categories(self):
        response = self.client.get(
            reverse("product-list"), {"sideload": "categories,old_categories"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_relation_names = ["products", "categories", "old_categories"]

        self.assertSetEqual(
            set(response.data.serializer.instance.keys()), {"products", "category"}
        )
        self.assertSetEqual(
            set(dict(response.data).keys()), set(expected_relation_names)
        )
