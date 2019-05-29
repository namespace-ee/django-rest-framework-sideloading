from rest_framework import viewsets

from drf_sideloading.mixins import SideloadableRelationsMixin, SelectableDataMixin
from tests.mixins import OtherMixin
from tests.models import Product, Category, Supplier, Partner
from tests.serializers import (
    ProductSerializer,
    CategorySerializer,
    SupplierSerializer,
    PartnerSerializer,
    ProductSideloadableSerializer,
    CategorySideloadableSerializer,
)


class ProductViewSet(SelectableDataMixin, SideloadableRelationsMixin, OtherMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloading_serializer_class = ProductSideloadableSerializer

    def get_serializer_class(self):
        # if no super is called sideloading should still work
        return self.serializer_class


class CategoryViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    sideloading_serializer_class = CategorySideloadableSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
