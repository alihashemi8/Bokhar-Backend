from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from discounts.models import Coupon, GlobalDiscount
from products.permission import IsSeller

from .serializers import CouponSerializer, GlobalDiscountSerializer
from .tasks_customer import send_sms_coupon, send_sms_global_discount


class CouponToCustomer(APIView):
    permission_classes = [IsSeller]

    def post(self, request, id):
        try:
            coupon = Coupon.objects.get(id=id)
        except Coupon.DoesNotExist:
            return Response(
                {"error": "همچین کد تخفیفی وجود ندارد"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not coupon.user:
            return Response(
                {"error": "این کوپن به کاربری متصل نیست"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CouponSerializer(coupon)
        send_sms_coupon.delay(coupon.id)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GlobalToCustomer(APIView):
    permission_classes = [IsSeller]

    def post(self, request, id):
        try:
            global_discount = GlobalDiscount.objects.get(id=id)
        except GlobalDiscount.DoesNotExist:
            return Response(
                {"error": "همچین کد تخفیفی وجود ندارد"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = GlobalDiscountSerializer(global_discount)
        send_sms_global_discount.delay(global_discount.id)
        return Response(serializer.data, status=status.HTTP_200_OK)
