from django.db import IntegrityError
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from products.permission import *

from .models import NotificationForAdvertising, NotificationForLate, SmsLog
from .serializers import *


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
# views.py
from rest_framework import status, viewsets
from rest_framework.response import Response

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


from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from order.models import Order, OrderStatus

from .tasks_customer import (send_sms_to_customer_canceled,
                             send_sms_to_customer_delivered,
                             send_sms_to_customer_paid)
from .tasks_seller import send_sms_to_seller_canceled


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
