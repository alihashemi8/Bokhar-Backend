from django.db import models

# Create your models here.
from django.db import models
from users.models import User
from product.models import Product


# Create your models here.

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.CASCADE,related_name='order_items')
    total_price = models.IntegerField(default=0)
    create_time = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(
        max_length=30,
        choices=[
            ("pending", "در انتظار"),
            ("washing", "در حال شستشو"),
            ("ready", "آماده تحویل"),
            ("sent", "ارسال شده"),
        ],
        default="pending"
    )
    def __str__(self):
        return self.user.username



class OrderItem(models.Model):#create shopping cart
    order = models.ForeignKey(Order, on_delete=models.CASCADE,related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,related_name='order_items')
    size = models.CharField(max_length=11,null=True,blank=True)
    service_type = models.CharField(max_length=50)
    material = models.CharField(max_length=50)
    quantity = models.IntegerField()
    price = models.PosetiveIntegerField()

    def __str__(self):
        return self.product.name



def generate_discount_code(length=8):
    """یک کد تصادفی با حروف بزرگ و اعداد می‌سازد"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))



class DiscountCode(models.Model):
    name = models.CharField(max_length=20, unique=True,null=True)
    percent = models.IntegerField(default=0)
    quantity = models.IntegerField(default=1)           # تعداد دفعات قابل استفاده
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if not self.name:  # اگر نام کد وارد نشده بود، خودکار بساز
            while True:
                code = generate_discount_code()
                if not DiscountCode.objects.filter(name=code).exists():
                    break
            self.name = code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name




