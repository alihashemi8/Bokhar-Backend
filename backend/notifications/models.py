from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import datetime

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from order.models import *
from products.models import *
from users.models import *



class SmsLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "در انتظار"),
        ("sent", "ارسال شد"),
        ("failed", "ناموفق"),
    ]

    SMS_TYPE_CHOICES = [
        ("order_paid", "پرداخت سفارش"),
        ("order_delivered", "تحویل سفارش"),
        ("order_canceled", "کنسلی سفارش"),
        ("seller_cancel_report", "گزارش کنسلی به فروشنده"),
        ("daily_report", "گزارش روزانه فروشنده"),
        ("coupon", "کوپن تخفیف"),
        ("global_discount", "تخفیف سراسری"),
        ("advertising", "تبلیغاتی"),
        ("late_notification", "یادآوری تأخیر"),
        ("other", "سایر"),
    ]

    phone_number = models.CharField(max_length=20, verbose_name="شماره گیرنده")
    message = models.TextField(verbose_name="متن پیامک")
    sms_type = models.CharField(
        max_length=30,
        choices=SMS_TYPE_CHOICES,
        default="other",
        verbose_name="نوع پیامک",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="وضعیت"
    )
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان ارسال")
    provider_response = models.TextField(
        null=True, blank=True, verbose_name="پاسخ سرویس پیامک"
    )

    # امکان اتصال به هر شیء مرتبط (سفارش، کوپن و...)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "گزارش پیامک"
        verbose_name_plural = "گزارش‌های پیامک"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_number", "sms_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"پیامک {self.get_sms_type_display()} به {self.phone_number} ({self.get_status_display()})"

    def mark_sent(self, response=None):
        """علامت‌گذاری به عنوان ارسال موفق"""
        self.status = "sent"
        self.sent_at = timezone.now()
        self.provider_response = response
        self.save(update_fields=["status", "sent_at", "provider_response"])

    def mark_failed(self, response=None):
        """علامت‌گذاری به عنوان ارسال ناموفق"""
        self.status = "failed"
        self.sent_at = timezone.now()
        self.provider_response = response
        self.save(update_fields=["status", "sent_at", "provider_response"])


class NotificationForAdvertising(models.Model):
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_notifications"
    )

    product_pricing = models.ManyToManyField(
        ProductPricingTab, blank=True, related_name="pricing_notifications"
    )

    title = models.CharField(max_length=100, null=True, blank=True)
    message = models.TextField()
    brand = models.CharField(max_length=100)
    link = models.CharField(max_length=100)
    create_time = models.DateTimeField(auto_now_add=True)
    month_key = models.CharField(max_length=7, editable=False)

    STATUS_CHOICES = [
        ("success", "ارسال موفق"),
        ("failed", "ارسال ناموفق"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "month_key"],
                name="uniq_ad_notification_per_month_per_user",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.month_key:
            now = timezone.now()
            self.month_key = f"{now.year:04d}-{now.month:02d}"
        self.full_clean()
        return super().save(*args, **kwargs)


class NotificationForLate(models.Model):
    title = models.CharField(max_length=100)
    message = models.TextField()

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="late_notifications"
    )

    STATUS_CHOICES = [
        ("success", "ارسال موفق"),
        ("failed", "ارسال ناموفق"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")

    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "create_time"]),
        ]
