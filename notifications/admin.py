from django.contrib import admin

from .models import *

# Register your models here.
admin.site.register(SmsLog)
admin.site.register(NotificationForLate)
admin.site.register(NotificationForAdvertising)
