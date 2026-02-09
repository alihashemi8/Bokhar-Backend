from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from users.models import User


# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="images/", null=True, blank=True)

    def __str__(self):
        return self.name


class Size(models.Model):
    meter = models.IntegerField(null=True, blank=True)
    single_double = models.IntegerField(null=True, blank=True)



class Product(models.Model):

    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    size = models.ForeignKey(Size,on_delete=models.CASCADE,null = True, blank=True, related_name="products")
    material = models.CharField(max_length=100)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    price_meter =  models.IntegerField(null=True, blank=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    # برای کد تخفبف  درصد
    discount_percent = models.PositiveIntegerField(null=True, blank=True)
    expiration_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(max_length=500, null=True, blank=True)
    service_type = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name},{self.category}"

    def save(self, *args, **kwargs):
        # فقط اگر محصول متری و size موجود است
        if self.price_meter is not None and self.size and self.size.meter:
            self.price = int(self.price_meter * self.size.meter)
        super().save(*args, **kwargs)

    @property
    def new_price(self):
        if (
                self.price
                and self.discount_percent
                and self.expiration_date
                and self.expiration_date > timezone.now()
        ):
            return int(self.price * (100 - self.discount_percent) / 100)
        return self.price
