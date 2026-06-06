from celery import shared_task
from django.contrib.auth import get_user_model

from .models import *

User = get_user_model()


@shared_task
def send_sms_coupon(coupon_id):
    """ارسال پیامک کوپن تخفیف به یک کاربر خاص"""
    try:
        coupon = Coupon.objects.select_related("user").get(id=coupon_id)
    except Coupon.DoesNotExist:
        return "کوپن مورد نظر یافت نشد"

    if not coupon.user:
        return "این کوپن به کاربری متصل نیست"

    # ساخت متن
    discount_text = (
        f"{coupon.value}% تخفیف"
        if coupon.type == "percent"
        else f"{coupon.value:,} تومان تخفیف"
    )
    min_text = (
        f" (حداقل خرید {coupon.min_order_price:,} تومان)"
        if coupon.min_order_price
        else ""
    )
    usage_limit = coupon.usage_limit if coupon.usage_limit else "نامحدود"

    full_message = (
        f"کاربر عزیز {coupon.user.fullname}\n"
        f"🎁 کد تخفیف: {coupon.code} | {discount_text}{min_text}\n"
        f"⏰ محدودیت استفاده: {usage_limit}"
    )

    # ایجاد لاگ
    log = SmsLog.objects.create(
        phone_number=coupon.user.phone,
        message=full_message,
        sms_type="coupon",
        status="pending",
        content_type=ContentType.objects.get_for_model(Coupon),
        object_id=coupon.id,
    )
    try:
        # send_sms(to=coupon.user.phone, message=full_message)
        log.mark_sent(response="test success")
        return f"پیامک کوپن برای {coupon.user.fullname} ارسال شد"
    except Exception as e:
        log.mark_failed(response=str(e))
        return f"خطا در ارسال پیامک کوپن: {e}"


@shared_task
def send_sms_global_discount(discount_id):
    """ارسال پیامک تخفیف سراسری به همه کاربران"""
    try:
        discount = GlobalDiscount.objects.get(id=discount_id)
    except GlobalDiscount.DoesNotExist:
        return "تخفیف سراسری مورد نظر یافت نشد"

    users = User.objects.filter(role="user")
    if not users.exists():
        return "هیچ کاربری یافت نشد"

    discount_text = (
        f"{discount.value}% تخفیف"
        if discount.type == "percent"
        else f"{discount.value:,} تومان تخفیف"
    )
    time_info = ""
    if discount.start_at or discount.end_at:
        time_info = " ("
        if discount.start_at:
            time_info += f"از {discount.start_at.strftime('%Y-%m-%d')}"
        if discount.end_at:
            time_info += f" تا {discount.end_at.strftime('%Y-%m-%d')}"
        time_info += ")"

    base_message = (
        "{user_name} عزیز\n"
        "🔥 تخفیف ویژه سراسری:\n\n"
        f"{discount_text}{time_info}\n\n"
        "🎁 این تخفیف روی تمام محصولات اعمال می‌شود!\n"
        "🛒 همین حالا خرید کنید"
    )

    content_type = ContentType.objects.get_for_model(GlobalDiscount)
    sent_count = 0
    failed_count = 0

    for user in users:
        message = base_message.replace("{user_name}", user.fullname)
        log = SmsLog.objects.create(
            phone_number=user.phone,
            message=message,
            sms_type="global_discount",
            status="pending",
            content_type=content_type,
            object_id=discount.id,
        )
        try:
            # send_sms(to=user.phone, message=message)
            log.mark_sent(response="test success")
            sent_count += 1
        except Exception as e:
            log.mark_failed(response=str(e))
            failed_count += 1

    return f"ارسال پیامک تخفیف سراسری به {sent_count} کاربر انجام شد (ناموفق: {failed_count})"


@shared_task
def send_sms_to_customer_delivered(
    id, customer_phone, customer_name, delivery_shift_text, delivery_date
):
    """
    ارسال پیامک به مشتری وقتی سفارشش تحویل داده شد
    """
    message = f"""
{customer_name} عزیز،
سفارش شما (کد پیگیری {id}) تحویل داده شد.
زمان تقریبی دریافت: {delivery_shift_text}
تاریخ: {delivery_date}

با تشکر از اعتماد شما
    """.strip()

    # پیدا کردن سفارش برای اتصال لاگ (اختیاری)
    try:
        order = Order.objects.get(id=id)
        content_type = ContentType.objects.get_for_model(Order)
        object_id = order.id
    except Order.DoesNotExist:
        content_type = None
        object_id = None

    log = SmsLog.objects.create(
        phone_number=customer_phone,
        message=message,
        sms_type="order_delivered",
        status="pending",
        content_type=content_type,
        object_id=object_id,
    )
    try:
        # send_sms(phone_number=customer_phone, message=message)
        log.mark_sent(response="test success")
        return f"SMS sent to {customer_phone} for order {id}"
    except Exception as e:
        log.mark_failed(response=str(e))
        return f"Error sending SMS: {e}"


@shared_task
def send_sms_to_customer_paid(order_data):
    """
    ارسال پیامک تایید پرداخت به مشتری
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
        f"{order.user.fullname} عزیز\n\n"
        f"✅ پرداخت شما با موفقیت انجام شد\n\n"
        f"📦 شماره پیگیری سفارش: {order.id}\n"
        f"💰 مبلغ پرداختی: {total_price:,} تومان\n"
        f"📅 تاریخ تحویل: {order.delivery_date}\n"
        f"⏰ شیفت تحویل: {order.delivery_shift}\n\n"
        f"🚚 وضعیت سفارش شما از طریق همین شماره اطلاع‌رسانی خواهد شد.\n\n"
        f"با تشکر از اعتماد شما 🙏"
    )

    log = SmsLog.objects.create(
        phone_number=order.user.phone,
        message=message,
        sms_type="order_paid",
        status="pending",
        content_type=ContentType.objects.get_for_model(Order),
        object_id=order.id,
    )
    try:
        # send_sms(to=order.user.phone, message=message)
        log.mark_sent(response="test success")
        return f"پیامک پرداخت موفق برای {order.user.fullname} ارسال شد"
    except Exception as e:
        log.mark_failed(response=str(e))
        return f"خطا در ارسال پیامک پرداخت: {e}"


@shared_task
def send_sms_to_customer_canceled(order_data):
    """
    ارسال پیامک کنسلی سفارش به مشتری
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
        f"{order.user.fullname} عزیز\n\n"
        f"✅ کنسلی سفارش شما با موفقیت انجام شد\n\n"
        f"📦 شماره پیگیری سفارش: {order.id}\n"
        f"💰 مبلغ برگشتی به کیف پول: {total_price:,} تومان\n"
        f"با تشکر از اعتماد شما 🙏"
    )

    log = SmsLog.objects.create(
        phone_number=order.user.phone,
        message=message,
        sms_type="order_canceled",
        status="pending",
        content_type=ContentType.objects.get_for_model(Order),
        object_id=order.id,
    )
    try:
        # send_sms(to=order.user.phone, message=message)
        log.mark_sent(response="test success")
        return f"برگشت به کیف پول موفق برای {order.user.fullname} ارسال شد"
    except Exception as e:
        log.mark_failed(response=str(e))
        return f"خطا در ارسال پیامک کنسلی: {e}"


@shared_task
def send_sms_for_advertising(id):
    if not id:
        return

    notification = (
        NotificationForAdvertising.objects.prefetch_related("product_pricing")
        .filter(id=id)
        .first()
    )
    if not notification:
        return

    service_names = notification.product_pricing.all()
    service_name_part = ", ".join([t.tab_name for t in service_names]) or "سرویس‌ها"

    text = (
        f"{service_name_part}\n"
        f"{notification.title or ''}\n"
        f"{notification.message}\n"
        f"برند: {notification.brand}\n"
        f"لینک: {notification.link}"
    ).strip()

    users = User.objects.all()
    content_type = ContentType.objects.get_for_model(NotificationForAdvertising)
    sent_count = 0
    failed_count = 0

    for user in users:
        log = SmsLog.objects.create(
            phone_number=user.phone,
            message=text,
            sms_type="advertising",
            status="pending",
            content_type=content_type,
            object_id=notification.id,
        )
        try:
            # send_sms(user.phone, text)
            log.mark_sent(response="test success")
            sent_count += 1
        except Exception as e:
            log.mark_failed(response=str(e))
            failed_count += 1

    return f"پیامک تبلیغاتی به {sent_count} کاربر ارسال شد (ناموفق: {failed_count})"


@shared_task
def send_sms_for_late(notif_id):
    if not notif_id:
        return

    notify = NotificationForLate.objects.filter(id=notif_id).first()

    if not notify:
        print("x")
        return

    text = f"{notify.title}\n{notify.message}\nکاربر: {notify.user}".strip()

    user = notify.user
    if not user or not hasattr(user, "phone"):
        return "کاربر یا شماره تلفن نامعتبر است"

    log = SmsLog.objects.create(
        phone_number=user.phone,
        message=text,
        sms_type="late_notification",
        status="pending",
        content_type=ContentType.objects.get_for_model(NotificationForLate),
        object_id=notify.id,
    )
    try:
        # send_sms(user.phone, text)
        log.mark_sent(response="test success")
        print(f"پیامک یادآوری برای {user.phone} ارسال شد")
        return f"پیامک یادآوری برای {user.phone} ارسال شد"
    except Exception as e:
        log.mark_failed(response=str(e))
        return f"خطا: {e}"
