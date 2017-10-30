from rest_framework import viewsets

from drf_sideloading.mixins import SideloadableRelationsMixin
from .models import Product, Category, Supplier, Partner
from .serializers import ProductSerializer, CategorySerializer, SupplierSerializer, PartnerSerializer


class ProductViewSet(SideloadableRelationsMixin, viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing and editing products.
    """


    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    sideloadable_relations = {
        'product': {'primary': True, 'serializer': ProductSerializer},
        'category': CategorySerializer,
        'supplier': SupplierSerializer,
        'partner': PartnerSerializer
    }

    # sideloadable_relations = {
    #     'product': {'primary': True, 'serializer': ProductSerializer},
    #     'category': {'serializer': CategorySerializer, 'name': 'categories'},
    #     'supplier': {'serializer': SupplierSerializer, 'name': 'suppliers'},
    #     'partner': PartnerSerializer
    # }
    # sideloadable_relations = {
    #     'product': {'primary': True, 'serializer': ProductSerializer},
    #     'category': {'serializer': CategorySerializer, 'name': 'categories'},
    #     'supplier': SupplierSerializer,
    #     'partner': PartnerSerializer
    # }


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
