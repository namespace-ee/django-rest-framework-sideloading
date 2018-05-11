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
        # definition is monkey patched in tests setup
    }


class CategoryViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    sideloadable_relations = {
        # definition is monkey patched in tests setup
    }


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
