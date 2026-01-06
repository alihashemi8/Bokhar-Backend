import uuid

from django.db import models

from users.models import User

# Create your models here.


class UserWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class WalletTransaction(models.Model):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

    WALLET_CHARGE = "wallet charge"
    ORDER_PAYMENT = "order payment"

    TYPE_CHOICES = (  # برای اینکه نوع پرداخت مشخص بشه
        (DEPOSIT, "Deposit"),
        (WITHDRAW, "Withdraw"),
    )

    STATUS_CHOICES = (  # وضعیت پرداخت
        (PENDING, "Pending"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
    )
    PURPOSE_CHOICES = (
        (WALLET_CHARGE, "Wallet Charge"),
        (ORDER_PAYMENT, "Order Payment"),
    )
    wallet = models.ForeignKey(
        UserWallet, on_delete=models.CASCADE, related_name="transactions"
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)  # تاریخ  تراکنش
    amount = models.BigIntegerField(default=0)
    reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
    )

    def __str__(self):
        return f"{self.type}-{self.amount}"
