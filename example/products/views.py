from rest_framework import viewsets

from drf_sideloading.mixins import SideloadableRelationsMixin
from .models import Product, Category, Supplier, Partner
from .serializers import ProductSerializer, CategorySerializer, SupplierSerializer, PartnerSerializer, \
    ProductSideloadableSerializer


class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloadable_serializer_class = ProductSideloadableSerializer


class CategoryViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    """
    A more complex ViewSet with reverse relations.
    """

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
