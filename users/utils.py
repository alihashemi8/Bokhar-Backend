import secrets
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password

OTP_EXPIRE = 120        # اعتبار OTP
OTP_COOLDOWN = 60       # فاصله بین ارسال
OTP_LIMIT = 3           # حداکثر در بازه
OTP_WINDOW = 600        # بازه 10 دقیقه
BASE_BLOCK_TIME = 180   # زمان بلاک پایه

def generate_otp(phone):
    code = str(secrets.randbelow(90000) + 10000)  
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

def validate_otp(phone, code, consume=False):
    """
    validate_otp: بررسی صحت کد
    consume=True: کد را حذف می‌کند (برای استفاده نهایی)
    consume=False: فقط بررسی می‌کند (برای pre-check فرانت)
    """
    # چک بلاک بودن
    if cache.get(f"otp_block:{phone}"):
        ttl = cache.ttl(f"otp_block:{phone}") or 0
        return False, f"شماره بلاک است. {ttl} ثانیه صبر کنید"

    saved_hash = cache.get(f"otp:{phone}")
    if not saved_hash:
        return False, "OTP منقضی شده یا ارسال نشده"

    if check_password(str(code), saved_hash):
        if consume:
            # حذف OTP و ریست خطاها در صورت مصرف نهایی
            cache.delete_many([
                f"otp:{phone}",
                f"otp_fail:{phone}",
                f"otp_block:{phone}",
            ])
        return True, "تأیید موفق"
    else:
        # ثبت خطا
        blocked, block_time = register_failed_attempt(phone)
        if blocked:
            return False, f"به دلیل تلاش زیاد بلاک شدید. {block_time} ثانیه صبر کنید"
        return False, "کد اشتباه است"

# alias برای استفاده در login/register (با consume=True)
def verify_otp(phone, code):
    return validate_otp(phone, code, consume=True)
