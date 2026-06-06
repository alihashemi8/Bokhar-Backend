from django.utils import timezone
from datetime import timedelta
from django.db import models
from .models import Order, OrderStatus, PickUpTemplate, DeliveryTemplate
import logging
logger = logging.getLogger(__name__)


def get_available_pickup_capacity(shift):
    """ظرفیت خالی تحویل‌گیری برای تاریخ و شیفت مشخص"""
    try:
        template = DeliveryTemplate.objects.get(time_shift=shift, is_active=True)
    except DeliveryTemplate.DoesNotExist:
        return 0




def get_available_delivery_capacity(order_type, date, shift):
    """
    ظرفیت خالی تحویل‌دهی با توجه به نوع سفارش (عادی/۲۴/۴۸ ساعته)
    order_type: خروجی متد order_range_type() (رشته فارسی)
    """
    try:
        template = DeliveryTemplate.objects.get(time_shift=shift, is_active=True)
    except DeliveryTemplate.DoesNotExist:
        return 0

    # فیلتر پایه: همه سفارش‌هایی که در این تاریخ و شیفت تحویل‌دهی دارند
    base_orders = Order.objects.filter(
        delivery_date=date,
        delivery_shift=shift
    )

    # سفارش‌هایی که ظرفیت تحویل‌دهی را اشغال می‌کنند
    used_all = base_orders.filter(
        models.Q(status__in=[
            OrderStatus.PAID,
            OrderStatus.PICKED_UP,
            OrderStatus.WASHING,
            OrderStatus.DELIVERED
        ])
    )

    # تفکیک ظرفیت بر اساس نوع سفارش
    if order_type == "سفارش فوری 24 ساعته":
        # فقط ظرفیت فوری ۲۴ ساعته مهم است
        capacity = template.urgent_24_capacity
        # سفارش‌های ۲۴ ساعته را از بین use_all جدا می‌کنیم
        urgent_24 = used_all.filter(order_type="سفارش فوری 24 ساعته").count()
        return max(0, capacity - urgent_24)

    elif order_type == "48ساعته":
        # ظرفیت ۴۸ ساعته (در صورت وجود فیلد مجزا)؛
        # اگر فیلد جداگانه برای ۴۸ ساعته ندارید، می‌توانید از ظرفیت کلی استفاده کنید
        capacity = template.urgent_48_capacity   # فیلد urgent_48_capacity در مدل موجود است
        urgent_48 = used_all.filter(order_type="48ساعته").count()
        return max(0, capacity - urgent_48)