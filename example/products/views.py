from rest_framework import viewsets

from drf_sideloading.mixins import SideloadableRelationsMixin, SelectableDataMixin
from .models import Product, Category, Supplier, Partner
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    SupplierSerializer,
    PartnerSerializer,
    ProductSideloadableSerializer,
    CategorySideloadableSerializer,
)


class ProductViewSet(SelectableDataMixin, SideloadableRelationsMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloading_serializer_class = ProductSideloadableSerializer


class CategoryViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    """
    A more complex ViewSet with reverse relations.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    sideloading_serializer_class = CategorySideloadableSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
