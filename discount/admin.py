from django.contrib import admin



# Register your models here.
from .models import *

admin.site.register(ProductDiscount)
admin.site.register(GlobalDiscount)
admin.site.register(Coupon)

