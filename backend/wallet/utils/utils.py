import time

from django.core.cache import cache
from rest_framework.exceptions import ValidationError

COOLDOWN_SECONDS = 120  # ۲ دقیقه قفل
MAX_ATTEMPTS = 3  # حداکثر تلاش مجاز
CACHE_TIMEOUT = 300  # ۵ دقیقه ماندگاری در کش


def check_payment_cooldown(user_id, action):
    """
    بررسی محدودیت نرخ درخواست برای یک کاربر و یک اکشن خاص.
    در صورتی که تعداد تلاش‌های ناموفق به سقف مجاز رسیده باشد و زمان قفل باقی مانده باشد، خطا صادر می‌کند.
    """
    key = f"payment_cooldown:{user_id}:{action}"
    data = cache.get(key)

    if data is None:
        return True

    attempts = data.get("attempts", 0)
    first_failure_timestamp = data.get("first_failure")

    # اگر تعداد تلاش‌ها مساوی یا بیشتر از حد مجاز باشد
    if attempts >= MAX_ATTEMPTS:
        now = time.time()
        elapsed = now - first_failure_timestamp

        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            raise ValidationError(
                f"تعداد تلاش‌های ناموفق شما بیش از حد مجاز است. لطفا {remaining} ثانیه دیگر مجدداً تلاش کنید."
            )
        else:
            # زمان قفل ۲ دقیقه به پایان رسیده است -> کش را پاک کن تا از نو شروع شود
            cache.delete(key)
            return True

    return True


def record_payment_failure(user_id, action):
    """ثبت و شمارش یک تلاش ناموفق در سیستم برای کاربر"""
    key = f"payment_cooldown:{user_id}:{action}"
    now = time.time()
    data = cache.get(key)

    if data is None:
        # اولین تلاش ناموفق: زمان فعلی را به عنوان شروع بازه ذخیره می‌کنیم
        data = {"attempts": 1, "first_failure": now}
    else:
        data["attempts"] += 1

    cache.set(key, data, timeout=CACHE_TIMEOUT)


def reset_payment_cooldown(user_id, action):
    """پاک کردن محدودیت کاربر (معمولاً پس از تایید نهایی و موفق تراکنش یا رفع خطا)"""
    cache.delete(f"payment_cooldown:{user_id}:{action}")
