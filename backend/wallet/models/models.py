import uuid
from datetime import timedelta
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from backend.order import Order
from backend.users.models import User
from backend.wallet.models.setting_payment_models import PaymentTerminal


# =========================================================
# IDEMPOTENCY
# =========================================================
def default_expires_at():
    return timezone.now() + timedelta(hours=24)


"""این مدل برای اینکه اگه کاربر دوباره درخواست داد کلید جدید با توجه به درخواست قبلیش ساخته نشه هر درخواست جدبد یک کلید"""


class IdempotencyKey(
    models.Model
):  # مثلا اگه نت ضعیف بود پرداخت موفق بود دوباره پرداخت نکنه پول ازش کم نشه

    key = models.UUIDField(unique = True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="idempotency_keys"
    )

    endpoint = models.CharField(max_length=255)  # برای کدام ادرس بوده

    request_hash = models.CharField(
        max_length=255
    )  # اگر درخواست جدید بود از اینجا میفهمد که پاسخ جدید بدهد

    response_status = models.IntegerField(null=True, blank=True)  # پاسخ http

    is_processed = models.BooleanField(default=False)  # درخواست پردازش شده ایا ؟

    locked_at = models.DateTimeField(null=True, blank=True)  # زمان قفل شدن درخواست

    response_data = models.JSONField(
        default=dict
    )  # دزخواست تکراری بود همون جواب برگردونه

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=default_expires_at)

    class Meta:
        ordering = ["-created_at"]




# =========================================================
# PAYMENT SESSION
# =========================================================
"""
مدیریت تراکنش ارتباط با درگاه و وضعیت پرداخت در چه حالتی است
"""


class PaymentSession(models.Model):
    class Type(models.TextChoices):
        WALLET = "wallet"
        GATEWAY = "gateway"

    class Status(models.TextChoices):
        INITIATED = "INITIATED"
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        PAID = "PAID"
        FAILED = "FAILED"
        CANCELED = "CANCELED"
        REFUNDED = "REFUNDED"
        EXPIRED = "EXPIRED"

    uuid = models.UUIDField(  # به جای ایدی چون امن تر است
        default=uuid.uuid4, editable=False, unique=True
    )
    type_pay = models.CharField(choices=Type.choices)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="payments")

    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )

    terminal = models.ForeignKey(
        PaymentTerminal,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )

    amount = models.BigIntegerField()

    fee_amount = models.BigIntegerField(default=0)  # کارمزد درگاه

    authority = models.CharField(  # بعد درخواست به زرین پال میده
        max_length=255, null=True, blank=True, unique=True
    )

    ref_id = models.CharField(  # شماره نهایی تراکنش
        max_length=255, null=True, blank=True, unique=True
    )

    curency = models.CharField(max_length=255, default="IRT")
    card_pan = models.CharField(max_length=30, blank=True)  # شماره ماسک شده کارت
    card_hash = models.CharField(max_length=255, blank=True, default="")
    # ای پی پرداخت کننده
    payer_ip = models.GenericIPAddressField(null=True, blank=True)
    # اطلاهات دستگاه /مرورگر
    user_agent = models.TextField(blank=True)
    # درخواست به درگاه
    gateway_request = models.JSONField(default=dict)
    # پاسخ اولیه درگاه قبل پرداخت کاربر
    gateway_response = models.JSONField(default=dict)
    # پاسخ وریفای
    verify_response = models.JSONField(default=dict)
    # درگاه چه داده  ای برمیگردون  بعد پرداخت
    callback_payload = models.JSONField(default=dict)

    response_code = models.IntegerField(null=True, blank=True)
    # پیام حطا علت شکست
    fail_reason = models.TextField(blank=True)
    expire_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.INITIATED
    )

    is_verified = models.BooleanField(default=False)

    paid_at = models.DateTimeField(null=True, blank=True)

    verified_at = models.DateTimeField(null=True, blank=True)

    refunded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["authority"]),
            models.Index(fields=["ref_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.uuid}"


# =========================================================
# PAYMENT ATTEMPT
# =====================================================
"""تلاش برای پرداخت چند بار تلاش کرده و تاریخچه درخواست """


class PaymentAttempt(models.Model):

    class Status(models.TextChoices):
        INITIATED = "initiated"
        CALLBACK_RECEIVED = "callback_received"
        VERIFIED = "verified"
        FAILED = "failed"

    payment = models.ForeignKey(
        PaymentSession, on_delete=models.CASCADE, related_name="attempts"
    )

    authority = models.CharField(max_length=255, db_index=True)

    ref_id = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=30, choices=Status.choices)

    gateway_response = models.JSONField(default=dict)

    callback_payload = models.JSONField(default=dict)

    payer_ip = models.GenericIPAddressField(null=True, blank=True)

    idempotency_ip = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["authority"]),
            models.Index(fields=["status"]),
        ]


# =========================================================
# WALLET
# =========================================================


class Wallet(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")

    available_balance = models.BigIntegerField(default=0)

    locked_balance = models.BigIntegerField(default=0)

    withdraw_blocked_util = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user}"


# =========================================================
#  TRANSACTION
# =========================================================


class Transaction(models.Model):

    class TransactionType(models.TextChoices):
        DEPOSIT = "deposit"
        PAYMENT = "payment"
        REFUNDTOWALLET = "refundwallet"
        WITHDRAWAL = "withdrawal"

    class Status(models.TextChoices):
        PENDING = "pending"
        SUCCESS = "success"
        FAILED = "failed"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    wallet = models.ForeignKey(
        Wallet,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    payment = models.ForeignKey(
        PaymentSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallet_transactions",
    )

    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)

    amount = models.BigIntegerField(validators=[MinValueValidator(1)])

    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    # شناسه رهگیری عملیات

    trace_id = models.UUIDField(default=uuid4, editable=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    user_agent = models.TextField(blank=True)

    description = models.TextField(blank=True)

    available_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]


# =========================================================
# WEBHOOK LOG
# =========================================================]


class PaymentWebhookLog(models.Model):

    terminal = models.ForeignKey(PaymentTerminal, on_delete=models.SET_NULL, null=True)
    # از اینجا میقهمیم کدوم پرداخت یا سفارشی... هست
    payload = models.JSONField()

    headers = models.JSONField(default=dict)
    # ذخیره امنیت
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    # ایا امضای دیجیتال درست بده؟
    signature_valid = models.BooleanField(default=False)
    # جلوگیری از دوباره پردازش
    processed = models.BooleanField(default=False)
    # جواب بررسی کنیم
    response_data = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["processed"]),
            models.Index(fields=["created_at"]),
        ]

    # =========================================================
    # REFUND REQUEST
    # =========================================================


class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
        REJECTED = "rejected"

    class Method(models.TextChoices):
        CARD = "card"
        PAYA = "paya"

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)  # اصلاح
    method = models.CharField(choices=Method.choices)
    user = models.ForeignKey(
        "backend.users.User", on_delete=models.PROTECT, related_name="withdrawal_requests"
    )
    wallet = models.ForeignKey(
        "backend.wallet.Wallet", on_delete=models.PROTECT, related_name="withdrawals"
    )
    amount = models.BigIntegerField(validators=[MinValueValidator(1)])

    # اجباری: مشخص می‌کند روی کدام تراکنش شارژ، استرداد انجام شود
    deposit_payment = models.ForeignKey(
        "backend.wallet.PaymentSession",
        on_delete=models.PROTECT,
        related_name="withdrawal_requests",
        help_text="تراکنش شارژی که باید به آن استرداد شود",
    )

    bank_name = models.CharField(max_length=100, blank=True)  # اختیاری
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    failure_reason = models.TextField(blank=True)
    idempotency_key = models.UUIDField(unique=True, default=uuid4)  # اصلاح

    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]


import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class RefundRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELED = "canceled"

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)  # اصلاح

    user = models.ForeignKey(
        "backend.users.User", on_delete=models.PROTECT, related_name="refund_requests"
    )

    order = models.ForeignKey(
        "backend.order.Order", on_delete=models.PROTECT, related_name="refund_requests"
    )

    payment = models.ForeignKey(
        "backend.wallet.PaymentSession",
        on_delete=models.PROTECT,
        related_name="refund_requests",
    )

    amount = models.BigIntegerField(validators=[MinValueValidator(1)])

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    reason = models.TextField(blank=True)

    idempotency_key = models.UUIDField(unique=True, default=uuid4)  # اصلاح

    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=[

                    "status",
                ]
            )
        ]
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name="refund_amount_gt_zero")
        ]


    def __str__(self):
        return str(self.uuid)
