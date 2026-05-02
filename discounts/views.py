from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions
from django.utils import timezone
from django.db.models import Q

from .models import ProductDiscount, GlobalDiscount, Coupon
from .serializers import ProductDiscountSerializer, GlobalDiscountSerializer, CouponSerializer

from rest_framework.response import Response
from rest_framework import status

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
    queryset = ProductDiscount.objects.all()
    serializer_class = ProductDiscountSerializer

    def create(self, request, *args, **kwargs):
        material_id = request.data.get("material")
        value = request.data.get("value")

        if not material_id:
            return Response(
                {"error": "material is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        qs = ProductDiscount.objects.filter(material_id=material_id)

        # ✅ حذف تخفیف
        if value in [None, "", 0, "0"]:
            qs.delete()
            return Response({"deleted": True}, status=status.HTTP_200_OK)

        # ✅ آماده‌سازی داده - اگر زمان ارسال نشده، پاک شود
        data = request.data.copy()
        if 'start_at' not in data:
            data['start_at'] = None
        if 'end_at' not in data:
            data['end_at'] = None

        # ✅ create یا update
        discount = qs.first()

        if discount:
            serializer = self.get_serializer(discount, data=data, partial=True)
            status_code = status.HTTP_200_OK
        else:
            serializer = self.get_serializer(data=data)
            status_code = status.HTTP_201_CREATED

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status_code)


# ---------------------------------------------------------
#   GlobalDiscount
# ---------------------------------------------------------
class GlobalDiscountViewSet(ModelViewSet):
    queryset = GlobalDiscount.objects.all()
    serializer_class = GlobalDiscountSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        qs = GlobalDiscount.objects.all()

        if self.action == "list":
            now = timezone.now()
            qs = qs.filter(
                Q(is_active=True),
                Q(start_at__isnull=True) | Q(start_at__lte=now),
                Q(end_at__isnull=True) | Q(end_at__gte=now),
            )

        return qs

# ---------------------------------------------------------
#   Coupon
# ---------------------------------------------------------
class CouponViewSet(ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        qs = Coupon.objects.all()

        if self.action == "list":
            now = timezone.now()
            qs = qs.filter(
                Q(is_active=True),
                Q(start_at__isnull=True) | Q(start_at__lte=now),
                Q(end_at__isnull=True) | Q(end_at__gte=now),
            )

        return qs
