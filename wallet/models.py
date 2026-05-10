from django.db import models

# Create your models here.
from django.db import models
from order.models import Order
from users.models import User
from datetime import datetime
from django.utils import timezone

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class WalletTransaction(models.Model):
    class TransactionType(models.TextChoices):
        DEPOSIT = "deposit", "شارژ کیف پول"
        PAYMENT = "payment", "پرداخت سفارش"
        REFUND = "refund", "بازگشت وجه"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.BigIntegerField()
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "initiated", "ایجاد شده"
        SUCCESS = "success", "موفق"
        FAILED = "failed", "ناموفق"
        REFUNDED = "refunded", "برگشت داده شده"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments",null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.BigIntegerField()
    # کد منحصر به فردی که بانک در مرحله اول می‌دهد (مثل Authority در زرین‌پال)
    authority = models.CharField(max_length=255, null=True, blank=True)
    # شماره پیگیری نهایی که بانک پس از تایید موفق می‌دهد
    ref_id = models.CharField(max_length=255, null=True, blank=True)
    # ذخیره پاسخ کامل بانک برای عیب‌یابی  در آینده
    extra_data = models.JSONField(default=dict)
    response_code = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)