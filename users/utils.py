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

    # --------------------------
    # برای دیباگ بدون Redis، می‌تونی خط بعد رو کامنت کنی
    # count = cache.get(key, 0)
    # --------------------------
    
    # اگر بخوای محدودیت واقعی فعال باشه، از کد اصلی استفاده کن
    # if count >= 5:
    #     ttl = cache.ttl(key) or 0  # زمان باقی‌مانده بر حسب ثانیه
    #     return False, ttl

    # cache.set(key, count + 1, timeout=180)  # 3 دقیقه

    # برای دیباگ سریع بدون Redis، همیشه اجازه بده
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

import secrets
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password

OTP_EXPIRE = 120        # اعتبار OTP
OTP_COOLDOWN = 60       # فاصله بین ارسال
OTP_LIMIT = 3           # حداکثر در بازه
OTP_WINDOW = 600        # بازه 10 دقیقه  در هر 10دقیقه فقط 3بار otp
BASE_BLOCK_TIME = 180   # زمان بلاک پایه

def generate_otp(phone):
    code = str(secrets.randbelow(99999) + 10000)

    cache.set(
        f"otp:{phone}",
        make_password(code),
        timeout=OTP_EXPIRE
    )

    return code


def can_send_otp(phone):


    if cache.get(f"otp_block:{phone}"):
        ttl = cache.ttl(f"otp_block:{phone}") or 0
        return False, f"شماره بلاک است. {ttl} ثانیه صبر کنید"


    if cache.get(f"otp_cooldown:{phone}"):
        ttl = cache.ttl(f"otp_cooldown:{phone}") or 0
        return False, f"لطفاً {ttl} ثانیه دیگر صبر کنید"


    try:
        count = cache.incr(f"otp_limit:{phone}")
    except ValueError:
        cache.set(f"otp_limit:{phone}", 1, timeout=OTP_WINDOW)
        count = 1


    if count > OTP_LIMIT:
        ttl = cache.ttl(f"otp_limit:{phone}") or OTP_WINDOW
        return False, f"بیش از حد مجاز درخواست داده‌اید. {ttl} ثانیه صبر کنید"


    cache.set(f"otp_cooldown:{phone}", True, timeout=OTP_COOLDOWN)

    return True, "مجاز"

def is_phone_blocked(phone):
    key = f"otp_block:{phone}"
    blocked = cache.get(key) is not None
    ttl = cache.ttl(key) or 0
    return blocked, ttl


def register_failed_attempt(phone):

    try:
        fails = cache.incr(f"otp_fail:{phone}")
    except ValueError:
        cache.set(f"otp_fail:{phone}", 1, timeout=OTP_WINDOW)
        fails = 1

    if fails >= 3:
        block_time = BASE_BLOCK_TIME * fails
        cache.set(f"otp_block:{phone}", True, timeout=block_time)
        cache.delete(f"otp_fail:{phone}")
        return True, block_time

    return False, 0


def verify_otp(phone, code):

    # چک بلاک بودن
    if cache.get(f"otp_block:{phone}"):
        ttl = cache.ttl(f"otp_block:{phone}") or 0
        return False, f"شماره بلاک است. {ttl} ثانیه صبر کنید"

    saved_hash = cache.get(f"otp:{phone}")

    if not saved_hash:
        return False, "OTP منقضی شده"

    if check_password(str(code), saved_hash):
        # ریست وضعیت
        cache.delete_many([
            f"otp:{phone}",
            f"otp_fail:{phone}",
            f"otp_block:{phone}",
        ])
        return True, "تأیید موفق"

    # ثبت خطا
    blocked, block_time = register_failed_attempt(phone)
    if blocked:
        return False, f"به دلیل تلاش زیاد بلاک شدید. {block_time} ثانیه صبر کنید"

    return False, "کد اشتباه است"