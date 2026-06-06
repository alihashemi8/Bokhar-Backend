from .models import *
from django.db import models

from backend.users.models import User


class FinancialAuditLog(models.Model):

    ACTIONS = (
        ("PAYMENT_INITIATED", "PAYMENT_INITIATED"),
        ("PAYMENT_VERIFIED", "PAYMENT_VERIFIED"),
        ("PAYMENT_FAILED", "PAYMENT_FAILED"),
        ("ORDER_CREATED", "ORDER_CREATED"),
        ("TRANSACTION_CREATED", "TRANSACTION_CREATED"),
        ("PAYMENT_CANCELED", "PAYMENT_CANCELED"),
        ("REFUND_CREATED", "REFUND_CREATED"),
        ("REFUND_COMPLETED", "REFUND_COMPLETED"),
        ("WITHDRAW_CREATED", "WITHDRAW_CREATED"),
        ("WITHDRAW_COMPLETED", "WITHDRAW_COMPLETED"),
        ("WITHDRAW_FAILED", "WITHDRAW_FAILED"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    action = models.CharField(max_length=50, choices=ACTIONS)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    payment = models.ForeignKey(PaymentSession, on_delete=models.SET_NULL, null=True, blank=True)

    withdrawal = models.ForeignKey(
        "backend.wallet.WithdrawalRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    old_data = models.JSONField(default=dict, blank=True)
    new_data = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


from .models import *

class WebhookEvent(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        PROCESSED = "PROCESSED"
        FAILED = "FAILED"

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    payment = models.ForeignKey(
        PaymentSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    authority = models.CharField(
        max_length=255,
        db_index=True,
    )

    payload = models.JSONField()

    headers = models.JSONField(
        default=dict
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    processed = models.BooleanField(
        default=False
    )

    retry_count = models.IntegerField(
        default=0
    )

    error_message = models.TextField(
        blank=True
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        indexes = [
            models.Index(fields=["authority"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]