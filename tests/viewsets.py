from rest_framework import viewsets

from drf_sideloading.mixins import SideloadableRelationsMixin
from tests.mixins import OtherMixin
from tests.models import Product, Category, Supplier, Partner
from tests.serializers import ProductSerializer, CategorySerializer, SupplierSerializer, PartnerSerializer


class ProductViewSet(SideloadableRelationsMixin, OtherMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloadable_relations = {
        'products': {'primary': True, 'serializer': ProductSerializer},
        'categories': {'serializer': CategorySerializer, 'source': 'category', 'prefetch': 'category'},
        'suppliers': {'serializer': SupplierSerializer, 'source': 'supplier', 'prefetch': 'supplier'},
        'partners': {'serializer': PartnerSerializer, 'source': 'partners', 'prefetch': 'partners'}
    }


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    sideloadable_relations = {
        'categories': {'primary': True, 'serializer': CategorySerializer},
        'products': {'serializer': ProductSerializer, 'source': 'products', 'prefetch': 'products'},
        'suppliers': {'serializer': SupplierSerializer, 'source': 'products__supplier', 'prefetch': 'products__supplier'},
        'partners': {'serializer': PartnerSerializer, 'source': 'products__partners', 'prefetch': 'products__partners'}
    }


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
