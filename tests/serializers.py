from rest_framework import serializers

from drf_sideloading.serializers import SideLoadableSerializer
from tests.models import Supplier, Category, Product, Partner


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["name"]


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["name"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["name", "category", "supplier", "partners"]


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


class ProductSideloadableSerializer(SideLoadableSerializer):
    products = ProductSerializer(many=True)
    categories = CategorySerializer(source="category", many=True)
    main_suppliers = SupplierSerializer(source="supplier", many=True)
    backup_suppliers = SupplierSerializer(source="backup_supplier", many=True)
    partners = PartnerSerializer(source="partner", many=True)
    combined_suppliers = SupplierSerializer(many=True)

    class Meta:
        primary = "products"
        prefetches = {
            "categories": "category",
            "main_suppliers": "supplier",
            "backup_suppliers": "backup_supplier",
            "partners": "partners",
            # These can be defined to always load them, else they will be copied over form all sources or selected sources only.
            "combined_suppliers": {
                "suppliers": ["supplier"],
                "backup_supplier": ["backup_supplier"],
            },
        }
