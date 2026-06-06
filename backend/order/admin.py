from django.contrib import admin

from .models import  *
# ثبت هر مدل جداگانه
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PickUpTemplate)
admin.site.register(DeliveryTemplate)
admin.site.register(OrderStatusLog)
