from celery import shared_task
from django.contrib.auth import get_user_model

from order.models import *

from .models import *

User = get_user_model()


@shared_task
def send_sms_to_seller_canceled(order_data):
    """
    ارسال پیامک کنسلی سفارش به مغازه‌دارها
    """
    try:
        order = Order.objects.select_related("user").get(
            id=order_data["id"],
        )
    except Order.DoesNotExist:
        return f"سفارش با شناسه {order_data.get('id')} یافت نشد"

    if not order.user:
        return "کاربری برای این سفارش وجود ندارد"

    total_price = order.final_price
    message = (
        f"مغازه‌دار عزیز\n\n"
        f"❌ کاربر {order.user.fullname} سفارش خود را کنسل کرد\n\n"
        f"📦 شماره پیگیری سفارش: {order.id}\n"
        f"💰 مبلغ برگشتی به کیف پول کاربر: {total_price:,} تومان\n"
    )

    seller = User.objects.filter(role="seller")
    content_type = ContentType.objects.get_for_model(Order)
    sent_count = 0
    failed_count = 0

    log = SmsLog.objects.create(
        phone_number=seller.phone,
        message=message,
        sms_type="seller_cancel_report",
        status="pending",
        content_type=content_type,
        object_id=order.id,
    )
    try:
        # send_sms(to=seller.phone, message=message)  # سرویس واقعی
        # فعلاً برای تست موفقیت شبیه‌سازی می‌کنیم
        log.mark_sent(response="test success")
        sent_count += 1
    except Exception as e:
        log.mark_failed(response=str(e))
        failed_count += 1

    return f"پیامک کنسلی سفارش {order.id} به {sent_count} فروشنده ارسال شد (ناموفق: {failed_count})"


@shared_task
def send_sms_to_seller_daily_report():
    """
    تسک روزانه برای مغازه‌دار: گزارش سفارش‌های امروز
    """
    today = timezone.now().date()
    orders = Order.objects.filter(delivery_date=today)

    if not orders.exists():
        return f"هیچ سفارشی برای امروز ({today}) وجود ندارد"

    count_morning = orders.filter(delivery_shift="MORNING").count()
    count_evening = orders.filter(delivery_shift="EVENING").count()

    message_parts = [f"📋 گزارش سفارش‌های امروز ({today}):"]
    if count_morning:
        message_parts.append(f"☀️ صبح (۸ تا ۱۳): {count_morning} سفارش")
    if count_evening:
        message_parts.append(f"🌙 عصر (۱۶ تا ۲۰): {count_evening} سفارش")

    full_message = "\n".join(message_parts)

    sellers = User.objects.filter(role="seller")
    # برای گزارش روزانه object_id مرتبط نیست، پس content_type را خالی می‌گذاریم
    sent_count = 0
    failed_count = 0

    for seller in sellers:
        log = SmsLog.objects.create(
            phone_number=seller.phone,
            message=full_message,
            sms_type="+daily_report",
            status="pending",
        )
        try:
            # send_sms(to=seller.phone, message=full_message)
            log.mark_sent(response="test success")
            sent_count += 1
        except Exception as e:
            log.mark_failed(response=str(e))
            failed_count += 1

    return f"گزارش روزانه به {sent_count} فروشنده ارسال شد (ناموفق: {failed_count})"
