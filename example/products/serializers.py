from rest_framework import serializers

from drf_sideloading.relations import SideloadableRelation, SideloadablePrimary
from drf_sideloading.serializers import SideLoadableSerializer
from .models import Product, Category, Supplier, Partner


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


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


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = '__all__'


class ProductSideloadableSerializer(SideLoadableSerializer):
    products = ProductSerializer(many=True, read_only=True)
    categories = CategorySerializer(source='category', many=True, read_only=True)
    suppliers = SupplierSerializer(source='supplier', many=True, read_only=True)
    partners = PartnerSerializer(source='partners', many=True, read_only=True)

    class Meta:
        primary = 'products'
        prefetches = {
            'categories': 'category',
            'suppliers': 'supplier',
            'partners': 'partners',
        }
