from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions
from django.utils import timezone
from django.db.models import Q

from .models import ProductDiscount, GlobalDiscount, Coupon
from .serializers import ProductDiscountSerializer, GlobalDiscountSerializer, CouponSerializer


# ---------------------------------------------------------
#   PERMISSION
# ---------------------------------------------------------
class IsSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and getattr(request.user, "role", None) == "seller"


# ---------------------------------------------------------
#   ProductDiscount
# ---------------------------------------------------------
class ProductDiscountViewSet(ModelViewSet):
    queryset = ProductDiscount.objects.all()  # برای DRF ضروری است
    serializer_class = ProductDiscountSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        now = timezone.now()
        return ProductDiscount.objects.filter(
            Q(is_active=True),
            Q(start_at__isnull=True) | Q(start_at__lte=now),
            Q(end_at__isnull=True) | Q(end_at__gte=now),
        )


# ---------------------------------------------------------
#   GlobalDiscount
# ---------------------------------------------------------
class GlobalDiscountViewSet(ModelViewSet):
    queryset = GlobalDiscount.objects.all()  # این خط باید باشد
    serializer_class = GlobalDiscountSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        now = timezone.now()
        return GlobalDiscount.objects.filter(
            Q(is_active=True),
            Q(start_at__isnull=True) | Q(start_at__lte=now),
            Q(end_at__isnull=True) | Q(end_at__gte=now),
        )


# ---------------------------------------------------------
#   Coupon
# ---------------------------------------------------------
class CouponViewSet(ModelViewSet):
    queryset = Coupon.objects.all()  # این خط نیز لازم است
    serializer_class = CouponSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        return Coupon.objects.all()
