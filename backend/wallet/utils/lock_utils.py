import logging
from django_redis import get_redis_connection
from redis.exceptions import LockError

logger = logging.getLogger(__name__)

class DistributedLock:

    def __init__(
        self,
        key: str,
        timeout: int = 60,
        blocking_timeout: int = 1
    ):
        self.redis = get_redis_connection("default")
        # ایجاد آبجکت کلاینت لاک ردیس
        self.lock = self.redis.lock(
            name=key,
            timeout=timeout,
            blocking_timeout=blocking_timeout
        )
        self.acquired = False

    def acquire(self) -> bool:
        try:
            self.acquired = self.lock.acquire()
            return self.acquired
        except LockError as e:
            logger.error(f"خطا در دریافت قفل توزیع‌شده برای کلید {self.lock.name}: {e}")
            self.acquired = False
            return False

    def release(self) -> None:
        if self.acquired:
            try:
                # متد داخلی release در کلاینت redis-py خودش بررسی owned() را انجام می‌دهد
                self.lock.release()
            except LockError as e:
                # اگر قفل قبلاً منقضی شده باشد یا مالکیت آن تغییر کرده باشد، خطا را لاگ می‌کنیم تا برنامه کرش نکند
                logger.warning(f"قفل توزیع‌شده برای کلید {self.lock.name} احتمالاً منقضی شده یا آزاد فرستاده شده است: {e}")
            finally:
                self.acquired = False

    # =========================================================
    # اضافه کردن قابلیت پشتیبانی از Context Manager (ساختار with)
    # =========================================================
    def __enter__(self):
        if not self.acquire():
            # در صورتی که نتواند قفل را بگیرد، خطا صادر می‌کند تا تراکنش ادامه پیدا نکند
            from rest_framework.exceptions import ValidationError
            raise ValidationError("درخواست شما در حال پردازش است، لطفاً چند لحظه صبر کنید.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()