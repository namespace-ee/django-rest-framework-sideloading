from rest_framework import serializers

from drf_sideloading.serializers import SideLoadableSerializer, SelectableDataSerializer
from .models import Product, Category, Supplier, Partner


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductSerializer(SelectableDataSerializer, serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


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
    partners = PartnerSerializer(many=True)

    class Meta:
        primary = "products"
        prefetches = {
            "categories": "category",
            "suppliers": "supplier",
            "partners": "partners",
        }
