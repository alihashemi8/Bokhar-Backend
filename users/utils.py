from .models import OTP
from django.utils import timezone
import random

RESEND_INTERVAL_SECONDS = 60 

def create_and_save_otp(phone, resend=False):
    now = timezone.now()
    latest_otp = OTP.objects.filter(phone=phone).order_by("-created_at").first()

    if latest_otp:
        if not latest_otp.is_expired() and resend:
            # بررسی فاصله زمانی resend
            elapsed = (now - latest_otp.created_at).total_seconds()
            if elapsed < RESEND_INTERVAL_SECONDS:
                raise Exception(f"لطفاً {int(RESEND_INTERVAL_SECONDS - elapsed)} ثانیه صبر کنید قبل از درخواست مجدد OTP")
            # حذف OTP قدیمی قبل از ایجاد OTP جدید
            latest_otp.delete()

    # ساخت OTP جدید
    otp_plain = str(random.randint(100000, 999999))
    otp_hash = OTP.hash_otp(otp_plain)

    OTP.objects.create(phone=phone, otp_hash=otp_hash)

    # ارسال پیامک یا لاگ کردن برای تست
    print(f"OTP for {phone}: {otp_plain}")  # تست در کنسول
    return otp_plain
