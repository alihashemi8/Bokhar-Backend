from rest_framework.routers import DefaultRouter
from .views import ProductDiscountViewSet, GlobalDiscountViewSet, CouponViewSet

router = DefaultRouter()
router.register("product-discounts", ProductDiscountViewSet, basename="productdiscount")
router.register("global-discounts", GlobalDiscountViewSet)
router.register("coupons", CouponViewSet)

urlpatterns = router.urls
