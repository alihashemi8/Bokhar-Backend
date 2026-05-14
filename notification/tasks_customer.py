from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from order.models import Order, OrderStatus
from .models import Coupon, GlobalDiscount, Notification

User = get_user_model()


@shared_task
def send_sms_coupon(coupon_id):
    """ارسال پیامک کوپن تخفیف به یک کاربر خاص"""
    try:
        coupon = Coupon.objects.select_related('user').get(id=coupon_id)
    except Coupon.DoesNotExist:
        return "کوپن مورد نظر یافت نشد"

    messages = []

    # تعیین متن تخفیف
    if coupon.type == 'percent':
        discount_text = f"{coupon.value}% تخفیف"
    else:
        discount_text = f"{coupon.value:,} تومان تخفیف"

    # حداقل خرید
    min_text = ""
    if coupon.min_order_price:
        min_text = f" (حداقل خرید {coupon.min_order_price:,} تومان)"

    messages.append(
        f"کد: {coupon.code} | {discount_text}{min_text}"
    )

    # محدودیت استفاده
    usage_limit = coupon.usage_limit if coupon.usage_limit else 'نامحدود'

    full_message = (
            f"کاربر عزیز {coupon.user.fullname}\n"
            f"🎁 کدهای تخفیف فعال شما:\n\n" +
            "\n".join(messages) +
            f"\n\n⏰ محدودیت استفاده: {usage_limit}"
    )

    print(full_message)
    # send_sms(to=coupon.user.phone, message=full_message)

    return f"پیامک کوپن برای {coupon.user.fullname} ارسال شد"


@shared_task
def send_sms_global_discount(discount_id):
    """ارسال پیامک تخفیف سراسری به همه کاربران"""
    try:
        discount = GlobalDiscount.objects.get(id=discount_id)
    except GlobalDiscount.DoesNotExist:
        return "تخفیف سراسری مورد نظر یافت نشد"

    users = User.objects.filter(role='user')

    if not users.exists():
        return "هیچ کاربری یافت نشد"

    # تعیین متن تخفیف
    if discount.type == 'percent':
        discount_text = f"{discount.value}% تخفیف"
    else:
        discount_text = f"{discount.value:,} تومان تخفیف"

    # اطلاعات زمان‌بندی
    time_info = ""
    if discount.start_at or discount.end_at:
        time_info = " ("
        if discount.start_at:
            time_info += f"از {discount.start_at.strftime('%Y-%m-%d')}"
        if discount.end_at:
            time_info += f" تا {discount.end_at.strftime('%Y-%m-%d')}"
        time_info += ")"

    discount_messages = [
        f"تخفیف سراسری | {discount_text}{time_info}"
    ]

    base_message = (
            "{user_name} عزیز\n"
            "🔥 تخفیف ویژه سراسری:\n\n" +
            "\n".join(discount_messages) +
            "\n\n🎁 این تخفیف روی تمام محصولات اعمال می‌شود!\n"
            "🛒 همین حالا خرید کنید"
    )

    # ارسال به همه کاربران
    sent_count = 0
    for user in users:
        message = base_message.replace("{user_name}", user.fullname)
        print(f"Sending to {user.phone}:\n{message}\n{'=' * 50}")
        # send_sms(to=user.phone, message=message)
        sent_count += 1

    return f"ارسال پیامک تخفیف سراسری به {sent_count} کاربر انجام شد"


@shared_task
def send_sms_to_customer_delivered(tracking_code, customer_phone, customer_name, delivery_shift_text, delivery_date):
    """
    ارسال پیامک به مشتری وقتی سفارشش تحویل داده شد
    """
    message = f"""
{customer_name} عزیز،
سفارش شما (کد پیگیری {tracking_code}) تحویل داده شد.
زمان تقریبی دریافت: {delivery_shift_text}
تاریخ: {delivery_date}

با تشکر از اعتماد شما
    """.strip()

    # تابع ارسال پیامک رو صدا بزنید
    # send_sms(phone_number=customer_phone, message=message)
    print(f"[SMS to {customer_phone}]:\n{message}\n{'-' * 40}")

    return f"SMS sent to {customer_phone} for order {tracking_code}"


@shared_task
def send_sms_to_customer_paid(order_data):
    """
    ارسال پیامک تایید پرداخت به مشتری
    """
    try:
        order = Order.objects.select_related('user').get(
            id=order_data['id'],
            tracking_code=order_data['tracking_code']
        )
    except Order.DoesNotExist:
        return f"سفارش با شناسه {order_data.get('id')} یافت نشد"

    if not order.user:
        return "کاربری برای این سفارش وجود ندارد"

    # محاسبه قیمت نهایی
    total_price = order.final_price

    # ساخت پیام
    message = (
        f"{order.user.fullname} عزیز\n\n"
        f"✅ پرداخت شما با موفقیت انجام شد\n\n"
        f"📦 شماره پیگیری سفارش: {order.tracking_code}\n"
        f"💰 مبلغ پرداختی: {total_price:,} تومان\n"
        f"📅 تاریخ تحویل: {order.delivery_date}\n"
        f"⏰ شیفت تحویل: {order.delivery_shift}\n\n"
        f"🚚 وضعیت سفارش شما از طریق همین شماره اطلاع‌رسانی خواهد شد.\n\n"
        f"با تشکر از اعتماد شما 🙏"
    )

    print(f"Sending SMS to {order.user.phone}:")
    print(message)
    print("=" * 60)

    # Uncomment when SMS service is ready:
    # send_sms(to=order.user.phone, message=message)

    return f"پیامک پرداخت موفق برای {order.user.fullname} ارسال شد"


@shared_task
def send_sms_to_customer_canceled(order_data):
    """
    ارسال پیامک کنسلی سفارش به مشتری
    """
    try:
        order = Order.objects.select_related('user').get(
            id=order_data['id'],
            tracking_code=order_data['tracking_code']
        )
    except Order.DoesNotExist:
        return f"سفارش با شناسه {order_data.get('id')} یافت نشد"

    if not order.user:
        return "کاربری برای این سفارش وجود ندارد"

    # محاسبه قیمت نهایی
    total_price = order.final_price

    # ساخت پیام
    message = (
        f"{order.user.fullname} عزیز\n\n"
        f"✅ کنسلی سفارش شما با موفقیت انجام شد\n\n"
        f"📦 شماره پیگیری سفارش: {order.id}\n"
        f"💰 مبلغ برگشتی به کیف پول: {total_price:,} تومان\n"
        f"با تشکر از اعتماد شما 🙏"
    )

    print(f"Sending SMS to {order.user.phone}:")
    print(message)
    print("=" * 60)

    # Uncomment when SMS service is ready:
    # send_sms(to=order.user.phone, message=message)

    return f"برگشت به کیف پول موفق برای {order.user.fullname} ارسال شد"

def send_sms_notify(notification):
    notif = Notification.objects.prefetch_related(
        prefetch_name='pricing_notifications'
    ).select_related('user').get(id= notification['id'])
    if not notif:
        return
    message = []
    for no in notif:
        for name in no.pricing_notification.all():
            message.append(name.tab_name)

    print(notif.title, notif.message,notif.brand,notif.link,message.join)


