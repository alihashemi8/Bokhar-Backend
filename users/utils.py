import random

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache

OTP_EXPIRE = 120


def generateOTP(phone):
    code = random.randint(100000, 999999)
    cache.set(
        f"otp:{phone}",
        make_password(str(code)),  # make به صورت هش شده ذخیره میشه
        timeout=OTP_EXPIRE,
    )
    return code


# قبل ارسال OTP
def can_send_otp(phone):
    key = f"otp_limit:{phone}"
    count = cache.get(key, 0)

    if count >= 5:
        ttl = cache.ttl(key) or 0  # زمان باقی‌مانده بر حسب ثانیه
        return False, ttl

    cache.set(key, count + 1, timeout=180)  # 3 دقیقه
    return True, 0


# برای بلاک شماره
def is_phone_blocked(phone):
    key = f"otp_block:{phone}"
    blocked = cache.get(key) is not None
    ttl = cache.ttl(key) or 0  # زمان باقی‌مانده بر حسب ثانیه
    return blocked, ttl


# ثبت تلاش ناموفق
def register_failed_attempt(phone):
    key = f"otp_fail:{phone}"
    fails = cache.get(key, 0)

    if fails >= 5:
        cache.set(f"otp_block:{phone}", True, timeout=180)
        ttl = cache.ttl(f"otp_block:{phone}") or 0
        cache.delete(key)  # ریست شمارنده خطا
        return True, ttl  # شماره بلاک شد

    cache.set(key, fails + 1, timeout=180)
    return False, 0


def verify_otp(phone, code):
    saved_hash = cache.get(f"otp:{phone}")

    if not saved_hash:
        return False

    if check_password(str(code), saved_hash):
        cache.delete(f"otp:{phone}")  # OTP یک‌بار مصرف
        return True

    return False
