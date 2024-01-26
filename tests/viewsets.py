from rest_framework import viewsets, filters, versioning
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet

from drf_sideloading.mixins import SideloadableRelationsMixin
from tests.mixins import OtherMixin
from tests.models import Product, Category, Supplier, Partner
from tests.serializers import (
    ProductSerializer,
    CategorySerializer,
    SupplierSerializer,
    PartnerSerializer,
    ProductSideloadableSerializer,
    CategorySideloadableSerializer,
    NewProductSideloadableSerializer,
)


class ProductViewSet(SideloadableRelationsMixin, OtherMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloading_serializer_class = ProductSideloadableSerializer
    versioning_class = versioning.AcceptHeaderVersioning
    filter_backends = [
        filters.SearchFilter,
        # django_filters.rest_framework.DjangoFilterBackend,
    ]
    search_fields = ["name"]

    # filter_fields = ["confirmed"]

    def get_serializer_class(self):
        # if no super is called sideloading should still work
        return self.serializer_class

    def get_sideloading_serializer_class(self):
        # if no super is called sideloading should still work
        if self.request.version == "2.0.0":
            return NewProductSideloadableSerializer
        return self.sideloading_serializer_class


class ListOnlyProductViewSet(SideloadableRelationsMixin, OtherMixin, ListModelMixin, GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloading_serializer_class = ProductSideloadableSerializer


class RetreiveOnlyProductViewSet(SideloadableRelationsMixin, OtherMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloading_serializer_class = ProductSideloadableSerializer


class ProductViewSetSideloadingBeforeViews(viewsets.ModelViewSet, SideloadableRelationsMixin, OtherMixin):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    sideloading_serializer_class = ProductSideloadableSerializer


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
