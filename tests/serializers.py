from rest_framework import serializers

from drf_sideloading.serializers import SideLoadableSerializer, SelectableDataSerializer
from tests.models import Supplier, Category, Product, Partner


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name"]


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["id", "name"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class ProductSerializer(SelectableDataSerializer, serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "category", "supplier", "partners"]


class CategorySideloadableSerializer(SideLoadableSerializer):
    categories = CategorySerializer(many=True)
    products = ProductSerializer(many=True)
    suppliers = SupplierSerializer(source="products__supplier", many=True)
    partners = PartnerSerializer(source="products__partners", many=True)

    class Meta:
        primary = "categories"
        prefetches = {
            "products": "products",
            "suppliers": "products__supplier",
            "partners": "products__partners",
        }


class ProductSideloadableSerializer(SelectableDataSerializer, SideLoadableSerializer):
    products = ProductSerializer(many=True)
    categories = CategorySerializer(source="category", many=True)
    suppliers = SupplierSerializer(source="supplier", many=True)
    partners = PartnerSerializer(source="partner", many=True)

    class Meta:
        primary = "products"
        prefetches = {
            "categories": "category",
            "suppliers": "supplier",
            "partners": "partners",
        }
