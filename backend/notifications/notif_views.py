from django.db import IntegrityError
from rest_framework import viewsets

from .serializers import *

from django.shortcuts import get_object_or_404
from rest_framework.decorators import action

from order.models import *

from .tasks_customer import (send_sms_to_customer_canceled,
                             send_sms_to_customer_delivered,
                             send_sms_to_customer_paid)
from .tasks_seller import send_sms_to_seller_canceled
from products.permission import *

class SmsLogViewSet(viewsets.ModelViewSet):
    queryset = SmsLog.objects.all()
    serializer_class = SmsLogSerializer
    permission_classes = [IsSeller]  # فقط ادمین

    def get_queryset(self):
        qs = super().get_queryset()
        phone = self.request.query_params.get("phone")
        sms_type = self.request.query_params.get("sms_type")
        status_filter = self.request.query_params.get("status")
        if phone:
            qs = qs.filter(phone_number__icontains=phone)
        if sms_type:
            qs = qs.filter(sms_type=sms_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save()


class NotificationForAdvertisingViewSet(viewsets.ModelViewSet):
    queryset = NotificationForAdvertising.objects.all()
    serializer_class = NotificationForAdvertisingSerializer
    permission_classes = [IsSeller]  # فقط ادمین

    def perform_create(self, serializer):
        try:
            instance = serializer.save()
            transaction.on_commit(lambda: send_sms_for_late.delay(instance.id))
        except IntegrityError as e:
            if "uniq_ad_notification_per_month_per_user" in str(e):
                raise serializers.ValidationError(
                    "شما قبلاً در این ماه یک اعلان تبلیغاتی ثبت کرده‌اید."
                )
            raise

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("month_key", None)
        self.perform_update(serializer)
        return Response(serializer.data)


from django.db import transaction
# order_views.py
from rest_framework import status, viewsets

from .models import NotificationForLate
from .serializers import NotificationForLateSerializer
from .tasks_customer import send_sms_for_late  # تسک سلری شما


class NotificationForLateViewSet(viewsets.ModelViewSet):
    queryset = NotificationForLate.objects.all()
    serializer_class = NotificationForLateSerializer
    # permission_classes = [IsSeller]   # ادمین

    def perform_create(self, serializer):
        instance = serializer.save()

        # بعد از کامیت شدن تراکنش (در صورت وجود)، تسک را اجرا کن
        transaction.on_commit(lambda: send_sms_for_late.delay(instance.id))


class OrderNotificationViewSet(viewsets.ViewSet):

    permission_classes = [IsSeller]
    """
    فقط مدیریت ارسال پیامک‌های مربوط به سفارش.
    """

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(Order, **filter_kwargs)
        return obj

    @action(detail=True, methods=["post"], url_path="send-sms")
    def send_order_sms(self, request, pk=None):
        instance = self.get_object()
        current_status = instance.status

        # ارسال پیامک بر اساس وضعیت فعلی سفارش
        if current_status == OrderStatus.PAID:
            order_data = {"id": instance.id, "user_id": instance.user_id}
            send_sms_to_customer_paid.delay(order_data)
            msg = f"تسک پیامک پرداخت موفق برای سفارش {pk} ارسال شد."

        elif current_status == OrderStatus.DELIVERED:
            shift_map = {
                "MORNING": "صبح (۸ تا ۱۳)",
                "EVENING": "عصر (۱۶ تا ۲۰)",
            }
            shift_text = shift_map.get(instance.delivery_shift, instance.delivery_shift)
            send_sms_to_customer_delivered.delay(
                id=instance.id,
                customer_phone=instance.user.phone,
                customer_name=instance.user.fullname or "مشتری گرامی",
                delivery_shift_text=shift_text,
                delivery_date=str(instance.delivery_date),
            )
            msg = f"تسک پیامک تحویل سفارش برای سفارش {pk} ارسال شد."

        elif current_status == OrderStatus.CANCELED:
            order_data = {"id": instance.id, "user_id": instance.user_id}
            send_sms_to_customer_canceled.delay(order_data)
            send_sms_to_seller_canceled.delay(order_data)
            msg = f"تسک پیامک کنسلی برای سفارش {pk} ارسال شد."

        else:
            return Response(
                {
                    "message": f"وضعیت فعلی سفارش {pk} ({current_status}) نیازی به ارسال پیامک ندارد."
                },
                status=status.HTTP_200_OK,
            )

        return Response({"message": msg}, status=status.HTTP_202_ACCEPTED)


from order.models import Order


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class NotificationsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "results": {
                "reminders": [
                    {
                        "id": 1,
                        "title": "یادآوری سفارش",
                        "message": "سفارش شما فردا ساعت ۸ تا ۱۲ تحویل گرفته می‌شود.",
                        "read": False,
                        "created_at": "2026-05-29T12:00:00"
                    },
                    {
                        "id": 2,
                        "title": "لباس آماده تحویل",
                        "message": "سفارش شماره #145 آماده تحویل است.",
                        "read": True,
                        "created_at": "2026-05-28T18:30:00"
                    }
                ],

                "discounts": [
                    {
                        "id": 1,
                        "title": "تخفیف ویژه",
                        "message": "۲۰٪ تخفیف برای اولین سفارش",
                        "percent": 20
                    },
                    {
                        "id": 2,
                        "title": "کد تخفیف تابستانه",
                        "message": "با کد SUMMER50 پنجاه هزار تومان تخفیف بگیرید.",
                        "percent": 15
                    }
                ],

                "transactions": [
                    {
                        "id": 1,
                        "amount": 250000,
                        "type": "پرداخت",
                        "created_at": "2026-05-27T15:20:00"
                    },
                    {
                        "id": 2,
                        "amount": 120000,
                        "type": "بازگشت وجه",
                        "created_at": "2026-05-25T10:15:00"
                    }
                ]
            }
        })