# -*- coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url, include
from rest_framework import routers

from tests import viewsets

router = routers.DefaultRouter()
router.register(r'product', viewsets.ProductViewSet)
router.register(r'category', viewsets.CategoryViewSet)
router.register(r'supplier', viewsets.SupplierViewSet)
router.register(r'partner', viewsets.PartnerViewSet)

urlpatterns = [
    url(r'^', include(router.urls))
]
