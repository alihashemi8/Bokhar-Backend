import random
import string
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

from products.models import *

DISCOUNT_TYPE_CHOICES = (
    ("percent", "درصدی"),
    ("fixed", "مبلغ ثابت"),
)

# ---------------------------------------------------------
# Helper Function
# ---------------------------------------------------------
def generate_discount_code(length=8):
    """تولید کد تصادفی الفبایی-عددی"""
    characters = string.ascii_uppercase + string.digits
    return "".join(random.choices(characters, k=length))


# ============================================================
# Product Discount (بدون تغییر)
# ============================================================
class ProductDiscount(models.Model):
    # ... (کدهای قبلی بدون تغییر) ...
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discounts",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="product_discounts",  # تغییر related_name برای جلوگیری از تداخل
    )
    pricing_tab = models.ForeignKey(
        ProductPricingTab,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discounts",
    )
    material = models.ForeignKey(
        MaterialPrice,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discounts",
    )

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.PositiveIntegerField()

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        targets = [
            self.product,
            self.category,
            self.pricing_tab,
            self.material,
        ]
        filled = [t for t in targets if t is not None]

        if len(filled) == 0:
            raise ValidationError("حداقل یک هدف تخفیف باید مشخص شود.")
        if len(filled) > 1:
            raise ValidationError("تنها یک هدف تخفیف می‌تواند انتخاب شود.")

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True

    def calculate_discount(self, base_price: int) -> int:
        if self.type == "percent":
            return (base_price * self.value) // 100
        return min(base_price, self.value)

    def __str__(self):
        return f"ProductDiscount {self.type} {self.value}"


# ============================================================
# Global Discount (بدون تغییر)
# ============================================================
class GlobalDiscount(models.Model):
    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.PositiveIntegerField()

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["start_at"]),
            models.Index(fields=["end_at"]),
        ]

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True

    def calculate_discount(self, base_price: int) -> int:
        if self.type == "percent":
            return (base_price * self.value) // 100
        return min(base_price, self.value)

    @classmethod
    def get_active_global_discount(cls):
        now = timezone.now()
        return (
            cls.objects.filter(is_active=True)
            .filter(
                models.Q(start_at__isnull=True) | models.Q(start_at__lte=now),
                models.Q(end_at__isnull=True) | models.Q(end_at__gte=now),
            )
            .order_by("-id")
            .first()
        )

    def __str__(self):
        return f"GlobalDiscount {self.type} {self.value}"


# ============================================================
# Coupon (اصلاح شده با تولید خودکار کد)
# ============================================================
class Coupon(models.Model):
    code = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True,  # اجازه خالی بودن برای تولید خودکار
        verbose_name="کد تخفیف"
    )

    type = models.CharField(
        max_length=10, 
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="نوع تخفیف"
    )
    value = models.PositiveIntegerField(verbose_name="مقدار")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="coupons",
        verbose_name="کاربر خاص (اختیاری)"
    )

    usage_limit = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name="حداکثر تعداد استفاده"
    )
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name="تعداد استفاده شده"
    )
    # نام فیلد با فرانت‌اند هماهنگ شد (min_order_amount)
    min_order_amount = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name="حداقل مبلغ سفارش"
    )

    # نام فیلد با فرانت‌اند هماهنگ شد (starts_at, ends_at)
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ شروع")
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پایان")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    created_at = models.DateTimeField(auto_now_add=True)  # برای مرتب‌سازی

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["starts_at"]),
            models.Index(fields=["ends_at"]),
        ]

    def save(self, *args, **kwargs):
        """تولید خودکار کد در صورت خالی بودن"""
        if not self.code:
            while True:
                new_code = generate_discount_code()
                if not Coupon.objects.filter(code=new_code).exists():
                    self.code = new_code
                    break
        super().save(*args, **kwargs)

    def is_valid_now(self, user=None, order_total=None):
        now = timezone.now()

        if not self.is_active:
            return False
        if self.user and self.user != user:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        if self.min_order_amount and order_total is not None:
            if order_total < self.min_order_amount:
                return False
        return True

    def calculate_discount(self, base_price: int) -> int:
        if self.type == "percent":
            return (base_price * self.value) // 100
        return min(base_price, self.value)

    def __str__(self):
        return f"Coupon {self.code}"
