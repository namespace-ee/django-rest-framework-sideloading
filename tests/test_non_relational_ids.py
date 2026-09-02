from django.urls import reverse
from rest_framework import status

from drf_sideloading.serializers import SideLoadableSerializer
from tests.models import Supplier, SupplierMetadata
from tests.serializers import PartnerSerializer, ProductSerializer, SupplierSerializer
from tests.test_products_api import BaseTestCase
from tests.viewsets import ProductViewSet


class NonRelationalIdSideloadTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class TempProductSideloadableSerializer(SideLoadableSerializer):
            products = ProductSerializer(many=True)
            suppliers = SupplierSerializer(many=True)
            extra_partners = PartnerSerializer(many=True, source="partner_ids")

            class Meta:
                primary = "products"
                prefetches = {
                    "suppliers": {
                        "supplier": ["supplier", "supplier__metadata"],
                        "legacy": ["legacy_supplier_id", "legacy_supplier_id__metadata"],
                    },
                    "extra_partners": ["partner_ids"],
                }

        cls._original_sideloading_serializer_class = ProductViewSet.sideloading_serializer_class
        ProductViewSet.sideloading_serializer_class = TempProductSideloadableSerializer

    @classmethod
    def tearDownClass(cls):
        ProductViewSet.sideloading_serializer_class = cls._original_sideloading_serializer_class
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.supplier5 = Supplier.objects.create(name="Supplier5")
        self.supplier_metadata_5 = SupplierMetadata.objects.create(
            supplier=self.supplier5, properties="Supplier5 metadata"
        )
        self.product1.legacy_supplier_id = self.supplier5.id
        self.product1.partner_ids = [self.partner3.id]
        self.product1.save(update_fields=["legacy_supplier_id", "partner_ids"])

    def test_list_sideload_suppliers_includes_legacy_id(self):
        response = self.client.get(
            reverse("product-list"),
            data={"sideload": "suppliers"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        body = response.json()
        self.assertEqual(["products", "suppliers"], list(body.keys()))
        names = {row["name"] for row in body["suppliers"]}
        self.assertIn("Supplier1", names)
        self.assertIn("Supplier5", names)

    def test_list_sideload_suppliers_source_filter_narrows_to_fk(self):
        response = self.client.get(
            reverse("product-list"),
            data={"sideload": "suppliers[supplier]"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        names = {row["name"] for row in response.json()["suppliers"]}
        self.assertIn("Supplier1", names)
        self.assertNotIn("Supplier5", names)

    def test_list_sideload_suppliers_source_filter_narrows_to_legacy_id(self):
        response = self.client.get(
            reverse("product-list"),
            data={"sideload": "suppliers[legacy]"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        names = {row["name"] for row in response.json()["suppliers"]}
        self.assertEqual({"Supplier5"}, names)
        supplier = response.json()["suppliers"][0]
        self.assertEqual("Supplier5 metadata", supplier["metadata"]["properties"])

    def test_list_sideload_extra_partners_uses_json_id_list(self):
        response = self.client.get(
            reverse("product-list"),
            data={"sideload": "extra_partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        body = response.json()
        self.assertEqual(["products", "extra_partners"], list(body.keys()))
        names = {row["name"] for row in body["extra_partners"]}
        self.assertEqual({"Partner3"}, names)

    def test_detail_sideload_extra_partners_uses_json_id_list(self):
        response = self.client.get(
            reverse("product-detail", args=[self.product1.id]),
            data={"sideload": "extra_partners"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        body = response.json()
        self.assertEqual(["products", "extra_partners"], list(body.keys()))
        names = {row["name"] for row in body["extra_partners"]}
        self.assertEqual({"Partner3"}, names)

    def test_detail_sideload_suppliers_includes_legacy_id(self):
        response = self.client.get(
            reverse("product-detail", args=[self.product1.id]),
            data={"sideload": "suppliers"},
            **self.DEFAULT_HEADERS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        names = {row["name"] for row in response.json()["suppliers"]}
        self.assertEqual({"Supplier1", "Supplier5"}, names)
