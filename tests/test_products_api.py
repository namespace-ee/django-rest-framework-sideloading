from django.db.models import Prefetch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status, serializers
from rest_framework.permissions import BasePermission
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.settings import api_settings

from drf_sideloading.serializers import SideLoadableSerializer
from tests.models import Category, Supplier, Product, Partner
from tests.serializers import (
    ProductSerializer,
    CategorySerializer,
    SupplierSerializer,
    PartnerSerializer,
)
from tests.viewsets import ProductViewSet


class BaseTestCase(TestCase):
    """Minimum common model setups"""

    DEFAULT_HEADERS = {
        # "content_type": "application/json",  # defaults to "application/octet-stream"
        "HTTP_ACCEPT": "application/json",
    }

    @classmethod
    def setUpClass(cls):
        super(BaseTestCase, cls).setUpClass()

    def setUp(self):
        self.category = Category.objects.create(name="Category")
        self.supplier1 = Supplier.objects.create(name="Supplier1")
        self.supplier2 = Supplier.objects.create(name="Supplier2")
        self.supplier3 = Supplier.objects.create(name="Supplier3")
        self.supplier4 = Supplier.objects.create(name="Supplier4")
        self.partner1 = Partner.objects.create(name="Partner1")
        self.partner2 = Partner.objects.create(name="Partner2")
        self.partner3 = Partner.objects.create(name="Partner3")
        self.partner4 = Partner.objects.create(name="Partner4")

        self.product1 = Product.objects.create(name="Product1", category=self.category, supplier=self.supplier1)
        self.product1.partners.add(self.partner1)
        self.product1.partners.add(self.partner2)
        self.product1.partners.add(self.partner4)
        self.product1.save()

        self.product2 = Product.objects.create(name="Product2", category=self.category, supplier=self.supplier2)
        self.product1.partners.add(self.partner2)
        self.product1.save()
        self.product3 = Product.objects.create(name="Product3", category=self.category, supplier=self.supplier3)
        self.product1.partners.add(self.partner3)
        self.product1.save()
        self.product4 = Product.objects.create(name="Product4", category=self.category, supplier=self.supplier4)


###################################
# Different Correct usages of API #
###################################
class ProductSideloadTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(ProductSideloadTestCase, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
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

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_list(self):
        response = self.client.get(path=reverse("product-list"), **self.DEFAULT_HEADERS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), list)
        self.assertEqual(4, len(response.json()))
        self.assertEqual("Product1", response.json()[0]["name"])

    def test_list_sideloading(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "categories,suppliers,partners"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "categories", "suppliers", "partners"], list(response.json().keys()))

    def test_list_partial_sideloading(self):
        """Test sideloading for selected relations"""
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "suppliers,partners"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "suppliers", "partners"], list(response.json().keys()))

    def test_detail(self):
        response = self.client.get(path=reverse("product-detail", args=[self.product1.id]), **self.DEFAULT_HEADERS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["name", "category", "supplier", "partners"], list(response.json().keys()))
        # TODO: check details

    def test_detail_sideloading(self):
        """Test sideloading for all defined relations in detail view"""
        response = self.client.get(
            path=reverse("product-detail", args=[self.product1.id]),
            data={"sideload": "categories,suppliers,partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "categories", "suppliers", "partners"], list(response.json().keys()))
        self.assertEqual(1, len(response.json().get("products")))
        # TODO: check details

    def test_detail_partial_sideloading(self):
        """Test sideloading for selected relations in detail view"""
        response = self.client.get(
            path=reverse("product-detail", args=[self.product1.id]),
            data={"sideload": "suppliers,partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "suppliers", "partners"], list(response.json().keys()))
        self.assertEqual(1, len(response.json().get("products")))
        # TODO: check details

    # all negative test cases below only here
    def test_sideload_param_empty_string(self):
        response = self.client.get(path=reverse("product-list"), data={"sideload": ""}, **self.DEFAULT_HEADERS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), list)
        self.assertEqual(4, len(response.json()))
        self.assertEqual("Product1", response.json()[0]["name"])

    def test_sideload_param_nonexistent_relation(self):
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "nonexistent"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual({"sideload": ["'nonexistent' is not one of the available choices."]}, response.json())

    def test_sideload_param_nonexistent_mixed_existing_relation(self):
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "nonexistent,suppliers"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual({"sideload": ["'nonexistent' is not one of the available choices."]}, response.json())

    def test_sideloading_param_wrongly_formed_query(self):
        response = self.client.get(
            path=reverse("product-list"),
            data={"sideload": ",,@,123,categories,123,.unexisting,123,,,,suppliers,!@"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual({"sideload": ["'@' is not one of the available choices."]}, response.json())


class ProductMultiSourceSideloadTestCase(BaseTestCase):
    """Test sideloading multiple related fields to a signle field"""

    @classmethod
    def setUpClass(cls):
        super(ProductMultiSourceSideloadTestCase, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            main_suppliers = SupplierSerializer(source="supplier", many=True)
            backup_suppliers = SupplierSerializer(source="backup_supplier", many=True)
            partners = PartnerSerializer(many=True)
            combined_suppliers = SupplierSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "main_suppliers": "supplier",
                    "backup_suppliers": "backup_supplier",
                    "partners": "partners",
                    # These can be defined to always load them, else they will be
                    # copied over form all sources or selected sources only.
                    "combined_suppliers": {
                        "suppliers": {"lookup": "supplier"},
                        "backup_suppliers": {"lookup": "backup_supplier"},
                    },
                }

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def setUp(self):
        super().setUp()
        self.product1.backup_supplier = self.supplier4
        self.product1.save()
        self.product2.backup_supplier = self.supplier3
        self.product2.save()
        self.product3.backup_supplier = self.supplier2
        self.product3.save()

    def test_list_sideloading_all(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(
            path=reverse("product-list"),
            data={
                "sideload": "categories,main_suppliers,backup_suppliers,combined_suppliers,partners",
                "search": self.product1.name,
            },
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(
            ["products", "categories", "main_suppliers", "backup_suppliers", "partners", "combined_suppliers"],
            list(response.json().keys()),
        )
        self.assertEqual(1, len(response.json()["products"]))
        self.assertSetEqual(
            {self.product1.supplier.name},
            {supplier["name"] for supplier in response.json()["main_suppliers"]},
        )
        self.assertSetEqual(
            {self.product1.backup_supplier.name},
            {supplier["name"] for supplier in response.json()["backup_suppliers"]},
        )
        self.assertSetEqual(
            {self.product1.supplier.name, self.product1.backup_supplier.name},
            {supplier["name"] for supplier in response.json()["combined_suppliers"]},
        )

    def test_list_sideloading_backup_suppliers(self):
        """Test sideloading for selected supplier relations"""
        response = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "combined_suppliers[backup_suppliers]", "search": self.product1.name},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "combined_suppliers"], list(response.json().keys()))
        self.assertEqual(1, len(response.json()["products"]))
        self.assertSetEqual(
            {self.product1.backup_supplier.name},  # regular supplier should not end up here.
            {supplier["name"] for supplier in response.json()["combined_suppliers"]},
        )

    def test_list_sideloading_combined_supplier(self):
        """Test sideloading for all supplier relations"""
        response = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "combined_suppliers", "search": self.product1.name},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "combined_suppliers"], list(response.json().keys()))
        self.assertEqual(1, len(response.json()["products"]))
        self.assertSetEqual(
            {
                self.product1.supplier.name,
                self.product1.backup_supplier.name,
            },  # regular supplier should not end up here.
            {supplier["name"] for supplier in response.json()["combined_suppliers"]},
        )

    def test_list_sideloading_combined_supplier_with_filtered_prefetch(self):
        """Test sideloading for all supplier relations"""
        response = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "combined_suppliers", "search": self.product1.name},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "combined_suppliers"], list(response.json().keys()))
        self.assertEqual(1, len(response.json()["products"]))
        self.assertSetEqual(
            {
                self.product1.supplier.name,
                self.product1.backup_supplier.name,
            },  # regular supplier should not end up here.
            {supplier["name"] for supplier in response.json()["combined_suppliers"]},
        )


###################################
# Different Correct usages of API #
###################################
class CategorySideloadTestCase(BaseTestCase):
    def test_list(self):
        response = self.client.get(path=reverse("category-list"), data={}, **self.DEFAULT_HEADERS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), list)
        self.assertEqual(1, len(response.json()))
        self.assertEqual("Category", response.json()[0]["name"])

    def test_list_sideloading_with_reverse_relations_and_its_relations(self):
        """Test sideloading for all defined relations"""
        response = self.client.get(
            path=reverse("category-list"), data={"sideload": "products,suppliers,partners"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["categories", "products", "suppliers", "partners"], list(response.json().keys()))

    def test_list_sideloading_with_reverse_relations_relations_without_the_reverse_relation_itself(self):
        """Test sideloading for related items to products, that are related to the categories
        while the products list itself is not sideloaded"""
        response = self.client.get(
            path=reverse("category-list"), data={"sideload": "suppliers,partners"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["categories", "suppliers", "partners"], list(response.json().keys()))


######################################################################################
# Incorrect definitions sideloadable_relations in ViewSet and SideloadableSerializer #
######################################################################################
class TestDrfSideloadingNoMetaClassDefined(BaseTestCase):
    """Run tests while including mixin but not defining sideloading"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoMetaClassDefined, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_correct_exception_raised(self):
        expected_error_message = "Sideloadable serializer must have a Meta class defined with the 'primary' field name!"
        with self.assertRaisesMessage(ValueError, expected_error_message):
            self.client.get(
                path=reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                **self.DEFAULT_HEADERS,
            )


class TestDrfSideloadingNoPrimaryDefined(BaseTestCase):
    """Run tests with invalid sideloadabale serializer setup (Meta primary_field not set)"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingNoPrimaryDefined, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                pass

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_correct_exception_raised(self):
        expected_error_message = "Sideloadable serializer must have a Meta class defined with the 'primary' field name!"
        with self.assertRaisesMessage(ValueError, expected_error_message):
            self.client.get(
                path=reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                **self.DEFAULT_HEADERS,
            )


class TestDrfSideloadingRelationsNotListSerializers(BaseTestCase):
    """Run tests with invalid sideloadabale serializer setup (fields not set as many=True)"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingRelationsNotListSerializers, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer()
            suppliers = SupplierSerializer()
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_correct_exception_raised(self):
        expected_error_message = "SideLoadable field 'categories' must be set as many=True"
        with self.assertRaisesMessage(ValueError, expected_error_message):
            self.client.get(
                path=reverse("product-list"), data={"sideload": "categories,suppliers,partners"}, **self.DEFAULT_HEADERS
            )


class TestDrfSideloadingInvalidPrimary(BaseTestCase):
    """Run tests with invalid sideloadabale serializer setup (invalid primary_field)"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrimary, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "other"

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_correct_exception_raised(self):
        expected_error_message = "Sideloadable serializer Meta.primary must point to a field in the serializer!"
        with self.assertRaisesMessage(ValueError, expected_error_message):
            self.client.get(
                path=reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                **self.DEFAULT_HEADERS,
            )


class TestDrfSideloadingInvalidPrefetchesType(BaseTestCase):
    """Run tests with invalid sideloadabale serializer setup (prefetches not described as a dict)"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrefetchesType, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
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

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_correct_exception_raised(self):
        expected_error_message = "Sideloadable serializer Meta attribute 'prefetches' must be a dict."
        with self.assertRaisesMessage(ValueError, expected_error_message):
            self.client.get(
                path=reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                **self.DEFAULT_HEADERS,
            )


class TestDrfSideloadingInvalidPrefetchesValuesType(BaseTestCase):
    """Run tests with invalid sideloadabale serializer setup (invalid prefetch types)"""

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrefetchesValuesType, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
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

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_correct_exception_raised(self):
        expected_error_message = "prefetch with type '<class 'int'>' is not implemented"
        with self.assertRaisesMessage(NotImplementedError, expected_error_message):
            self.client.get(
                path=reverse("product-list"),
                data={"sideload": "categories,suppliers,partners"},
                **self.DEFAULT_HEADERS,
            )


class TestDrfSideloadingValidPrefetches(BaseTestCase):
    """
    Run tests with prefetch is user defined and another prefetch for the same relation is also created.
    Preftch.to_attr is not set. This should be automatically be set by our code.
    """

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingValidPrefetches, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            filtered_suppliers = SupplierSerializer(many=True)
            filtered_suppliers2 = SupplierSerializer(many=True)
            partners = PartnerSerializer(many=True)
            filtered_partners = PartnerSerializer(many=True)
            combined_suppliers = SupplierSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    "partners": ["partners"],
                    "filtered_suppliers": Prefetch(
                        lookup="supplier",
                        queryset=Supplier.objects.filter(name__in=["Supplier2", "Supplier4"]),
                        to_attr="filtered_suppliers",
                    ),
                    "filtered_suppliers2": Prefetch(
                        lookup="supplier",
                        queryset=Supplier.objects.filter(name__in=["Supplier3"]),
                        to_attr="filtered_suppliers2",
                    ),
                    "filtered_partners": Prefetch(
                        lookup="partners",
                        queryset=Partner.objects.filter(name__in=["Partner2", "Partner4"]),
                        to_attr="filtered_partners",
                    ),
                    "combined_suppliers": {
                        "filtered_suppliers": Prefetch(
                            lookup="supplier",
                            queryset=Supplier.objects.filter(name__in=["Supplier2", "Supplier4"]),
                            to_attr="filtered_suppliers",
                        ),
                        "filtered_suppliers2": Prefetch(
                            lookup="supplier",
                            queryset=Supplier.objects.filter(name__in=["Supplier3"]),
                            to_attr="filtered_suppliers2",
                        ),
                        "filtered_partners": Prefetch(
                            lookup="partners",
                            queryset=Partner.objects.filter(name__in=["Partner2", "Partner4"]),
                            to_attr="filtered_partners",
                        ),
                    },
                }

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_sideloading_with_dual_usage_prefetches(self):
        response_2 = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "categories,suppliers,partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response_2.status_code, status.HTTP_200_OK, response_2.data)
        self.assertIsInstance(response_2.json(), dict)
        self.assertListEqual(["products", "categories", "suppliers", "partners"], list(response_2.json().keys()))
        # check suppliers and partners are the same as from previous query!
        supplier_names = {supplier["name"] for supplier in response_2.json()["suppliers"]}
        self.assertSetEqual({"Supplier1", "Supplier2", "Supplier3", "Supplier4"}, supplier_names)
        partner_names = {partner["name"] for partner in response_2.json()["partners"]}
        self.assertSetEqual({"Partner1", "Partner2", "Partner3", "Partner4"}, partner_names)

    # # fixme: for some reason, the filtered_suppliers is not sideloaded altho Prefetch present in queryset arguments
    # #  because queryset is called as a generator maybe? In that case, the prefetches do nothing
    # def test_sideloading_normally(self):
    #     response_1 = self.client.get(
    #         path=reverse("product-list"),
    #         data={"sideload": "categories,suppliers,filtered_suppliers,partners,filtered_partners"},
    #         **self.DEFAULT_HEADERS,
    #     )
    #     self.assertEqual(response_1.status_code, status.HTTP_200_OK, response.json())
    #     self.assertIsInstance(response_1.json(), dict)
    #     self.assertListEqual(
    #         ["products", "categories", "suppliers", "filtered_suppliers", "partners", "filtered_partners"],
    #         list(response_1.json().keys()),
    #     )
    #     # check filtered_suppliers and filtered_partners are different from suppliers and partners!
    #     supplier_names = {partner["name"] for partner in response_1.json()["suppliers"]}
    #     self.assertSetEqual({"Supplier1", "Supplier2", "Supplier3", "Supplier4"}, supplier_names)
    #
    #     filtered_supplier_names = {partner["name"] for partner in response_1.json()["filtered_suppliers"]}
    #     self.assertSetEqual({"Supplier2", "Supplier4"}, filtered_supplier_names)
    #
    #     partner_names = {partner["name"] for partner in response_1.json()["partners"]}
    #     self.assertSetEqual({"Partner1", "Partner2", "Partner3", "Partner4"}, partner_names)
    #
    #     filtered_partner_names = {partner["name"] for partner in response_1.json()["filtered_partners"]}
    #     self.assertSetEqual({"Partner2", "Partner4"}, filtered_partner_names)
    #
    # # fixme: for some reason, the filtered_suppliers is not sideloaded altho Prefetch present in queryset arguments
    # def test_sideloading_with_filtered_prefetch(self):
    #     response_1 = self.client.get(
    #         path=reverse("product-list"),
    #         data={"sideload": "filtered_suppliers,filtered_partners"},
    #         **self.DEFAULT_HEADERS,
    #     )
    #     self.assertEqual(response_1.status_code, status.HTTP_200_OK, response.json())
    #     self.assertIsInstance(response_1.json(), dict)
    #     self.assertListEqual(
    #         ["products", "filtered_suppliers", "filtered_partners"],
    #         list(response_1.json().keys()),
    #     )
    #     filtered_supplier_names = {partner["name"] for partner in response_1.json()["filtered_suppliers"]}
    #     self.assertSetEqual({"Supplier2", "Supplier4"}, filtered_supplier_names)
    #
    #     filtered_partner_names = {partner["name"] for partner in response_1.json()["filtered_partners"]}
    #     self.assertSetEqual({"Partner2", "Partner4"}, filtered_partner_names)
    #
    # # fixme: for some reason, the filtered_suppliers is not sideloaded altho Prefetch present in queryset arguments
    # def test_sideloading_with_filtered_prefetches(self):
    #     response_1 = self.client.get(
    #         path=reverse("product-list"),
    #         data={"sideload": "categories,filtered_suppliers,filtered_suppliers2,filtered_partners"},
    #         **self.DEFAULT_HEADERS,
    #     )
    #     self.assertEqual(response_1.status_code, status.HTTP_200_OK, response.json())
    #     self.assertIsInstance(response_1.json(), dict)
    #     self.assertListEqual(
    #         ["products", "categories", "filtered_suppliers", "filtered_suppliers2", "filtered_partners"],
    #         list(response_1.json().keys()),
    #     )
    #     # check filtered_suppliers and filtered_partners are different from suppliers and partners!
    #
    #     filtered_supplier_names = {supplier["name"] for supplier in response_1.json()["filtered_suppliers"]}
    #     self.assertSetEqual({"Supplier2", "Supplier4"}, filtered_supplier_names)
    #
    #     filtered_supplier_names = {supplier["name"] for supplier in response_1.json()["filtered_suppliers2"]}
    #     self.assertSetEqual({"Supplier3"}, filtered_supplier_names)
    #
    #     filtered_partner_names = {partner["name"] for partner in response_1.json()["filtered_partners"]}
    #     self.assertSetEqual({"Partner2", "Partner4"}, filtered_partner_names)
    #
    # # fixme: for some reason, the filtered_suppliers is not sideloaded altho Prefetch present in queryset arguments
    # def test_sideloading_combined_suppliers_with_filtered_prefetches(self):
    #     response_1 = self.client.get(
    #         path=reverse("product-list"),
    #         data={"sideload": "categories,filtered_suppliers,filtered_partners"},
    #         **self.DEFAULT_HEADERS,
    #     )
    #     self.assertEqual(response_1.status_code, status.HTTP_200_OK, response.json())
    #     self.assertIsInstance(response_1.json(), dict)
    #     self.assertListEqual(
    #         ["products", "categories", "filtered_suppliers", "filtered_partners"],
    #         list(response_1.json().keys()),
    #     )
    #     # check filtered_suppliers and filtered_partners are different from suppliers and partners!
    #
    #     filtered_supplier_names = {partner["name"] for partner in response_1.json()["filtered_suppliers"]}
    #     self.assertSetEqual({"Supplier2", "Supplier4"}, filtered_supplier_names)
    #
    #     filtered_partner_names = {partner["name"] for partner in response_1.json()["filtered_partners"]}
    #     self.assertSetEqual({"Partner2", "Partner4"}, filtered_partner_names)


class TestDrfSideloadingInvalidPrefetchSource(BaseTestCase):
    """
    Run tests with prefetch is user defined and another prefetch for the same relation is also created.
    Preftch.to_attr is not set. This should be automatically be set by our code.
    """

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrefetchSource, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            filtered_suppliers = SupplierSerializer(source="supplier", many=True, read_only=True)
            filtered_suppliers2 = SupplierSerializer(source="supplier", many=True, read_only=True)
            partners = PartnerSerializer(many=True)
            filtered_partners = PartnerSerializer(source="partners", many=True, read_only=True)
            combined_suppliers = SupplierSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    "filtered_suppliers": Prefetch(
                        lookup="supplier",
                        queryset=Supplier.objects.filter(name__in=["Supplier2", "Supplier4"]),
                        to_attr="filtered_suppliers",
                    ),
                    "filtered_suppliers2": Prefetch(
                        lookup="supplier",
                        queryset=Supplier.objects.filter(name__in=["Supplier3"]),
                        to_attr="filtered_suppliers2",
                    ),
                    "filtered_partners": Prefetch(
                        lookup="partners",
                        queryset=Partner.objects.filter(name__in=["Partner2", "Partner4"]),
                        to_attr="filtered_partners",
                    ),
                    "combined_suppliers": {
                        "filtered_suppliers": Prefetch(
                            lookup="supplier",
                            queryset=Supplier.objects.filter(name__in=["Supplier2", "Supplier4"]),
                            to_attr="filtered_suppliers",
                        ),
                        "filtered_suppliers2": Prefetch(
                            lookup="supplier",
                            queryset=Supplier.objects.filter(name__in=["Supplier3"]),
                            to_attr="filtered_suppliers2",
                        ),
                        "filtered_partners": Prefetch(
                            lookup="partners",
                            queryset=Partner.objects.filter(name__in=["Partner2", "Partner4"]),
                            to_attr="filtered_partners",
                        ),
                    },
                }

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_sideloading_combined_suppliers_with_mismatching_to_attr_and_source(self):
        msg = (
            "ideloadable field 'filtered_suppliers' Prefetch 'to_attr' can't be different from source defined. "
            "Tip: Remove source from field serializer."
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.client.get(
                path=reverse("product-list"),
                data={"sideload": "filtered_suppliers"},
                **self.DEFAULT_HEADERS,
            )


class TestDrfSideloadingValidPrefetchObjectsImplicit(BaseTestCase):
    """
    Run tests with prefetch is user defined and another prefetch for the same relation is also created.
    Preftch.to_attr is not set. add field name as default.
    """

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingValidPrefetchObjectsImplicit, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            filtered_suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    # "partners": ["products__partners"],
                    "filtered_suppliers": Prefetch(
                        lookup="supplier",
                        queryset=Supplier.objects.filter(name__in=["Supplier2", "Supplier4"]),
                        # to_attr="filtered_suppliers",
                    ),
                }

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    # TODO: fix test as we get an error: "Two different prefetches for the same attribute"
    # def test_sideloading_with_prefetch_object_without_to_attr(self):
    #     msg = f"Either source or prefetches must be set for sideloadable field 'partners'"
    #     with self.assertRaisesMessage(ValueError, msg):
    #         self.client.get(
    #             path=reverse("product-list"),
    #             data={"sideload": "categories,suppliers,filtered_suppliers,partners"},
    #             **self.DEFAULT_HEADERS,
    #         )


class TestDrfSideloadingPrefetchObjectsMatchingLookup(BaseTestCase):
    """
    Use Prefetch object on a field where lookup matches field name
    """

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingPrefetchObjectsMatchingLookup, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    "partners": Prefetch(
                        lookup="partners",
                        queryset=Partner.objects.filter(name__in=["Partner2", "Partner4"]),
                        # to_attr="partners",  # we are testing a case where this is not set.
                    ),
                }

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_sideloading_with_prefetch_object_without_to_attr_but_lookup_matching_field(self):
        response_1 = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "categories,partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response_1.status_code, status.HTTP_200_OK, response_1.data)
        self.assertIsInstance(response_1.json(), dict)
        self.assertListEqual(
            ["products", "categories", "partners"],
            list(response_1.json().keys()),
        )
        # check filtered_suppliers and filtered_partners are different from suppliers and partners!
        # partner_names = {partner["name"] for partner in response_1.json()["partners"]}
        # FIXME: the Prefetch does not filter the queryset as expected!
        # self.assertSetEqual({"Partner2", "Partner4"}, partner_names)


class TestDrfSideloadingInvalidPrefetchObject(BaseTestCase):
    """
    Run tests with prefetch is user defined and another prefetch for the same relation is also created.
    Preftch.to_attr is invlalid
    """

    @classmethod
    def setUpClass(cls):
        super(TestDrfSideloadingInvalidPrefetchObject, cls).setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            filtered_suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)
            filtered_partners = PartnerSerializer(source="partners", many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    "filtered_suppliers": Prefetch(
                        lookup="supplier",
                        queryset=Supplier.objects.filter(name__in=["Supplier2", "Supplier4"]),
                        to_attr="wrong_field",
                    ),
                    # "partners": None,
                    "filtered_partners": Prefetch(
                        lookup="partners",
                        queryset=Partner.objects.filter(name__in=["Partner2", "Partner4"]),
                        to_attr="wrong_field_2",
                    ),
                }

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    # # TODO: fix this for cases where field source is present but Prefetch.to_attr mismatches
    # def test_sideloading_with_prefetches(self):
    #     msg = f"Either source or prefetches must be set for sideloadable field 'partners'"
    #     with self.assertRaisesMessage(ValueError, msg):
    #         self.client.get(
    #             path=reverse("product-list"),
    #             data={"sideload": "categories,suppliers,filtered_suppliers,partners"},
    #             **self.DEFAULT_HEADERS,
    #         )


class TestDrfSideloadingWithoutListModelMixin(BaseTestCase):
    def test_list(self):
        response = self.client.get(
            path=reverse("productretreiveonly-list"),
            data={"sideload": "categories"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_detail(self):
        response = self.client.get(
            path=reverse("productretreiveonly-detail", args=[self.product1.id]),
            data={"sideload": "categories"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())


class TestDrfSideloadingWithoutRetreiveModelMixin(BaseTestCase):
    def test_list(self):
        response = self.client.get(
            path=reverse("productlistonly-list"),
            data={"sideload": "categories"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())

    def test_detail(self):
        response = self.client.get(
            path=reverse("productlistonly-detail", args=[self.product1.id]),
            data={"sideload": "categories"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestDrfSideloadingListModelMixinAfterSideloading(BaseTestCase):
    # in case the DRF views are added after sideloading,
    # the list and retreive methods will be overwritten and no sideloading happens.

    def test_list(self):
        response = self.client.get(
            path=reverse("productwrongmixinorder-list"),
            data={"sideload": "categories,suppliers,filtered_suppliers,partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), list)

    def test_detail(self):
        response = self.client.get(
            path=reverse("productwrongmixinorder-detail", args=[self.product1.id]),
            data={"sideload": "categories,suppliers,filtered_suppliers,partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["name", "category", "supplier", "partners"], list(response.json().keys()))


class TestDrfSideloadingBrowsableApiPermissions(BaseTestCase):
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
                raise ValueError("This must not be called, when sideloadading is used!")

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {
                    "categories": "category",
                    "suppliers": ["supplier"],
                    # "partners": None,
                }

        ProductViewSet.renderer_classes = (BrowsableAPIRenderer, JSONRenderer)
        ProductViewSet.permission_classes = (ProductPermission,)
        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    @classmethod
    def tearDownClass(cls):
        ProductViewSet.renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
        ProductViewSet.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
        super(TestDrfSideloadingBrowsableApiPermissions, cls).tearDownClass()

    def test_sideloading_does_not_render_forms_and_check_object_permissions(self):
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "categories,suppliers,partners"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "categories", "suppliers", "partners"], list(response.json().keys()))

    def test_sideloading_allow_post_without_sideloading(self):
        category = Category.objects.create(name="Category")
        supplier = Supplier.objects.create(name="Supplier")

        headers = {"HTTP_ACCEPT": "application/json"}
        response = self.client.post(
            path=reverse("product-list"),
            data={
                "name": "Random product",
                "category": category.id,
                "supplier": supplier.id,
                "partners": [],
            },
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(isinstance(response.json(), dict))
        self.assertListEqual(["name", "category", "supplier", "partners"], list(response.json().keys()))

    def test_sideloading_allow_post_with_sideloading(self):
        # TODO: check response with new detail view sideloading logic!
        category = Category.objects.create(name="Category")
        supplier = Supplier.objects.create(name="Supplier")

        headers = {"HTTP_ACCEPT": "application/json"}
        response = self.client.post(
            path="{}{}".format(reverse("product-list"), "?sideload=categories,suppliers,partners"),
            data={
                "name": "Random product",
                "category": category.id,
                "supplier": supplier.id,
                "partners": [],
            },
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(isinstance(response.json(), dict))
        self.assertListEqual(["name", "category", "supplier", "partners"], list(response.json().keys()))


class ProductSideloadSameSourceDuplicationTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(ProductSideloadSameSourceDuplicationTestCase, cls).setUpClass()

        class OldCategorySerializer(serializers.ModelSerializer):
            old_name = serializers.CharField(source="name")

            class Meta:
                model = Category
                fields = ["old_name"]

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            categories = CategorySerializer(source="category", many=True)
            old_categories = OldCategorySerializer(source="category", many=True)
            suppliers = SupplierSerializer(source="supplier", many=True)
            partners = PartnerSerializer(many=True)

            class Meta:
                primary = "products"
                prefetches = {"category": "category", "old_categories": "category"}

        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    def test_list_sideload_categories(self):
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "categories"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "category"], list(response.data.serializer.instance.keys()))
        self.assertListEqual(["products", "categories"], list(response.json().keys()))

    def test_list_sideload_old_categories(self):
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "old_categories"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "category"], list(response.data.serializer.instance.keys()))
        self.assertListEqual(["products", "old_categories"], list(response.json().keys()))

    def test_list_sideload_new_categories_and_old_categories(self):
        response = self.client.get(
            path=reverse("product-list"), data={"sideload": "categories,old_categories"}, **self.DEFAULT_HEADERS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "category"], list(response.data.serializer.instance.keys()))
        self.assertListEqual(["products", "categories", "old_categories"], list(response.json().keys()))


class VersionesSideloadableSerializerTestCase(BaseTestCase):
    def test_list_sideload_categories(self):
        # old as example
        response = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "categories"},
            # headers:
            HTTP_ACCEPT="application/json; version=1.0",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "categories"], list(response.json().keys()))

        # new version can't sideload this value
        response = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "categories"},
            # headers:
            HTTP_ACCEPT="application/json; version=2.0.0",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual({"sideload": ["'categories' is not one of the available choices."]}, response.json())

        # new version called correctly
        response = self.client.get(
            path=reverse("product-list"),
            data={"sideload": "new_categories"},
            # headers:
            HTTP_ACCEPT="application/json; version=2.0.0",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertIsInstance(response.json(), dict)
        self.assertListEqual(["products", "new_categories"], list(response.json().keys()))
