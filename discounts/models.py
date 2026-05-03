from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

from products.models import (
    Product,
    Category,
    ProductPricingTab,
    MaterialPrice,
)

DISCOUNT_TYPE_CHOICES = (
    ("percent", "درصدی"),
    ("fixed", "مبلغ ثابت"),
)


# ============================================================
# Product Discount
# ============================================================
class ProductDiscount(models.Model):
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
        related_name="discounts",
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
# Global Discount
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
# Coupon
# ============================================================
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.PositiveIntegerField()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="coupons",
    )

    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    min_order_price = models.PositiveIntegerField(null=True, blank=True)

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def is_valid_now(self, user=None, order_total=None):
        now = timezone.now()

        if not self.is_active:
            return False
        if self.user and self.user != user:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        if self.min_order_price and order_total is not None:
            if order_total < self.min_order_price:
                return False
        return True

    def calculate_discount(self, base_price: int) -> int:
        if self.type == "percent":
            return (base_price * self.value) // 100
        return min(base_price, self.value)

    def __str__(self):
        return f"Coupon {self.code}"
