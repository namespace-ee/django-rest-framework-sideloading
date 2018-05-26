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


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class ProductSideloadableSerializer(SideLoadableSerializer):
    products = SideloadablePrimary(serializer=ProductSerializer)
    categories = SideloadableRelation(serializer=CategorySerializer, source='category', prefetch='category')
    suppliers = SideloadableRelation(serializer=SupplierSerializer, source='supplier', prefetch='supplier')
    partners = SideloadableRelation(serializer=PartnerSerializer, source='partners', prefetch='partners')


