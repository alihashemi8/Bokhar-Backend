from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from discounts.models import ProductDiscount, GlobalDiscount, Coupon
from discounts.serializers import (
    ProductDiscountSerializer,
    GlobalDiscountSerializer,
    CouponSerializer
)


class IsSeller(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user.is_authenticated and
            request.user.role == "seller"
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user.is_authenticated and
            request.user.role == "seller"
        )


class ProductDiscountViewSet(ModelViewSet):
    queryset = ProductDiscount.objects.all()
    serializer_class = ProductDiscountSerializer
    permission_classes = [IsSeller]


class GlobalDiscountViewSet(ModelViewSet):
    queryset = GlobalDiscount.objects.all()
    serializer_class = GlobalDiscountSerializer
    permission_classes = [IsSeller]


class CouponViewSet(ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsSeller]
