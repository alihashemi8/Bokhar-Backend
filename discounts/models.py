from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product, Category, ProductPricingTab

User = get_user_model()


class ProductDiscount(models.Model):
    DISCOUNT_TYPE = (
        ("percent", "Percent"),
        ("fixed", "Fixed"),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)

    pricing_tab = models.ForeignKey(ProductPricingTab, on_delete=models.CASCADE, null=True, blank=True)

    material = models.CharField(max_length=100, null=True, blank=True)

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE)
    value = models.FloatField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Discount {self.value} {self.type}"


class GlobalDiscount(models.Model):
    DISCOUNT_TYPE = (
        ("percent", "Percent"),
        ("fixed", "Fixed"),
    )

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE)
    value = models.FloatField()

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Global {self.value} {self.type}"
class Coupon(models.Model):

    DISCOUNT_TYPE = (
        ("percent", "Percent"),
        ("fixed", "Fixed"),
    )

    code = models.CharField(max_length=50, unique=True)

    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE)
    value = models.FloatField()

    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code
