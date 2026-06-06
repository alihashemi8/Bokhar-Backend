from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Size(models.Model):
    meter = models.IntegerField(null=True, blank=True)
    single_double = models.IntegerField(null=True, blank=True)

    def __str__(self):
        if self.meter:
            return f"{self.meter} متر"
        return f"{self.single_double} نفره"


class Product(models.Model):
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
    ]
    
    title = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name="products"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    base_price = models.PositiveIntegerField(default=0, help_text="حداقل قیمت برای نمایش")

    def __str__(self):
        return f"{self.title} - {self.category}"

    # ----------------------------------------------------
    #   🔥 متد گم‌شده — اضافه شد
    # ----------------------------------------------------
    def get_pricing_dict(self):
        """
        خروجی تمام تب‌ها + قیمت‌های جنس‌ها
        ساختار JSON درست مطابق ورودی و خروجی frontend
        """
        result = {}

        for tab in self.pricing_tabs.all():
            result[tab.tab_name] = {
                "sizeType": tab.size_type,
                "materialPrices": [
                    {
                        "material": mp.material,
                        "price": mp.price
                    }
                    for mp in tab.material_prices.all()
                ]
            }

        return result


class ProductPricingTab(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name="pricing_tabs"
    )
    tab_name = models.CharField(max_length=50)
    size_type = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['product', 'tab_name']

    def __str__(self):
        return f"{self.product.title} - {self.tab_name}"


class MaterialPrice(models.Model):
    pricing_tab = models.ForeignKey(
        ProductPricingTab,
        on_delete=models.CASCADE,
        related_name="material_prices"
    )
    material = models.CharField(max_length=50)
    price = models.PositiveIntegerField()

    class Meta:
        unique_together = ['pricing_tab', 'material']
