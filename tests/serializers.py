from rest_framework import serializers

from drf_sideloading.serializers import SideLoadableSerializer
from tests.models import Supplier, Category, Product, Partner, ProductMetadata, SupplierMetadata


class SupplierMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierMetadata
        fields = ["supplier", "properties"]


class SupplierSerializer(serializers.ModelSerializer):
    metadata = SupplierMetadataSerializer(read_only=True)

    class Meta:
        model = Supplier
        fields = ["name", "metadata"]


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["name"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name"]


class ProductMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMetadata
        fields = ["product", "properties"]


class ProductSerializer(serializers.ModelSerializer):
    metadata = ProductMetadataSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ["name", "category", "supplier", "partners", "metadata"]


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
    metadata = ProductMetadataSerializer(many=True, read_only=True)

    class Meta:
        primary = "products"
        prefetches = {
            "categories": "category",
            "main_suppliers": ["supplier", "supplier__metadata"],
            "backup_suppliers": ["backup_supplier", "backup_supplier__metadata"],
            "partners": "partners",
            # These can be defined to always load them, else they will be
            # copied over form all sources or selected sources only.
            "combined_suppliers": {
                "suppliers": ["supplier", "supplier__metadata"],
                "backup_supplier": ["backup_supplier", "backup_supplier__metadata"],
            },
            "metadata": "metadata",
        }


class NewProductSideloadableSerializer(SideLoadableSerializer):
    products = ProductSerializer(many=True)
    new_categories = CategorySerializer(source="category", many=True)
    new_main_suppliers = SupplierSerializer(source="supplier", many=True)
    new_backup_suppliers = SupplierSerializer(source="backup_supplier", many=True)
    new_partners = PartnerSerializer(source="partner", many=True)
    combined_suppliers = SupplierSerializer(many=True)
    metadata = ProductMetadataSerializer(many=True, read_only=True)

    class Meta:
        primary = "products"
        prefetches = {
            "new_categories": "category",
            "new_main_suppliers": ["supplier", "supplier__metadata"],
            "new_backup_suppliers": ["backup_supplier", "backup_supplier__metadata"],
            "new_partners": "partners",
            # These can be defined to always load them, else they will be
            # copied over form all sources or selected sources only.
            "combined_suppliers": {
                "suppliers": ["supplier", "supplier__metadata"],
                "backup_supplier": ["backup_supplier", "backup_supplier__metadata"],
            },
            "metadata": "metadata",
        }
