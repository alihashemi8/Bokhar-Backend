from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from order.models import Order, OrderStatus
from .tasks import (
    send_sms_to_customer_delivered,
    send_sms_to_customer_canceled,
    send_sms_to_seller_canceled,
    send_sms_to_customer_paid
)


@receiver(pre_save, sender=Order)
def capture_old_status(sender, instance, **kwargs):
    """
    قبل از ذخیره، وضعیت قبلی رو از دیتابیس می‌خونیم
    """
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status = old_order.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def notify_on_status_change(sender, instance, created, **kwargs):
    """
    مدیریت تمام نوتیفیکیشن‌های تغییر وضعیت سفارش
    """
    if created:
        return

    old_status = getattr(instance, '_old_status', None)

    if not old_status or old_status == instance.status:
        return

    # ارسال پیامک پرداخت موفق
    if instance.status == OrderStatus.PAID and old_status != OrderStatus.PAID:
        order_data = {
            "id": instance.id,
            "tracking_code": instance.tracking_code,
            "user_id": instance.user_id,
        }
        send_sms_to_customer_paid.delay(order_data)

    # ارسال پیامک تحویل سفارش
    elif instance.status == OrderStatus.DELIVERED and old_status != OrderStatus.DELIVERED:
        shift_map = {
            'MORNING': 'صبح (۸ تا ۱۳)',
            'EVENING': 'عصر (۱۶ تا ۲۰)',
        }
        shift_text = shift_map.get(instance.delivery_shift, instance.delivery_shift)

        send_sms_to_customer_delivered.delay(
            tracking_code=instance.tracking_code,
            customer_phone=instance.user.phone,
            customer_name=instance.user.fullname or 'مشتری گرامی',
            delivery_shift_text=shift_text,
            delivery_date=str(instance.delivery_date)
        )

    # ارسال پیامک کنسلی سفارش
    elif instance.status == OrderStatus.CANCELED and old_status == OrderStatus.PAID:
        order_data = {
            "id": instance.id,
            "tracking_code": instance.tracking_code,
            "user_id": instance.user_id,
        }
        send_sms_to_customer_canceled.delay(order_data)
        send_sms_to_seller_canceled.delay(order_data)