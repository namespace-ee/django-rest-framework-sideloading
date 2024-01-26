from django.urls import path, include
from rest_framework import routers

from tests import viewsets

router = routers.DefaultRouter()
router.register(r"product", viewsets.ProductViewSet)
router.register(r"productlistonly", viewsets.ListOnlyProductViewSet, basename="productlistonly")
router.register(
    r"productwrongmixinorder", viewsets.ProductViewSetSideloadingBeforeViews, basename="productwrongmixinorder"
)
router.register(r"productretreiveonly", viewsets.RetreiveOnlyProductViewSet, basename="productretreiveonly")
router.register(r"category", viewsets.CategoryViewSet)
router.register(r"supplier", viewsets.SupplierViewSet)
router.register(r"partner", viewsets.PartnerViewSet)

urlpatterns = [path("", include(router.urls))]
