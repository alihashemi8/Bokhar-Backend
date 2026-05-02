from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from products.models import Product, Category, ProductPricingTab, MaterialPrice


DISCOUNT_TYPE_CHOICES = (
    ("percent", "درصدی"),
    ("fixed", "مبلغ ثابت"),
)


# ============================================================
#   Product Discount  (product / category / tab / material)
# ============================================================
class ProductDiscount(models.Model):
    material = models.ForeignKey(
        MaterialPrice,
        on_delete=models.CASCADE,
        related_name="discounts"
    )

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.PositiveIntegerField()

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # --------------------------------------------------------
    # فقط یک هدف باید انتخاب شود
    # --------------------------------------------------------
    def clean(self):
        # validate material exists
        if not self.material:
            raise ValidationError("material الزامی است")
        
        # validate single target
        targets = [self.product, self.category, self.pricing_tab, self.material]
        filled = [t for t in targets if t is not None]
        
        if len(filled) == 0:
            raise ValidationError("حداقل یک فیلد هدف تخفیف باید مشخص شود.")
        if len(filled) > 1:
            raise ValidationError("تنها یک فیلد هدف تخفیف باید توسط آن پر شود.")

# ============================================================
#   Global Discount (Single Winner among global types)
# ============================================================
class GlobalDiscount(models.Model):
    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.PositiveIntegerField()

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['start_at']),
            models.Index(fields=['end_at']),
        ]

    def __str__(self):
        return f"GlobalDiscount {self.type} {self.value}"

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True


# ============================================================
#   Coupon  (Later integrated with Order)
# ============================================================
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.PositiveIntegerField()

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="coupons")

    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    min_order_price = models.PositiveIntegerField(null=True, blank=True)

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['start_at']),
            models.Index(fields=['end_at']),
        ]

    def __str__(self):
        return f"Coupon {self.code}"

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
