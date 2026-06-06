from django.db import models

from backend.users.models import User


class PaymentTerminal(models.Model):
    """
    مدل درگاه پرداخت (Terminal) مطابق با API زرین‌پال
    """

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        ACTIVE = "active", "فعال"
        SUSPENDED = "suspended", "معلق"
        REJECTED = "rejected", "رد شده"
        DELETED = "deleted", "حذف شده"

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_terminals"
    )
    terminal_id = models.CharField(
        max_length=225,
        unique=True,
        db_index=True,
        help_text="شناسه درگاه در زرین‌پال (همان id)",
    )
    merchant_id = models.CharField(
        unique=True, max_length=255, help_text="مرچنت کد (key)"
    )
    mcc = models.CharField(
        null=True, blank=True, max_length=10, help_text="کد دسته‌بندی صنف"
    )
    support_phone = models.CharField(max_length=15)
    name = models.CharField(max_length=255)
    logo = models.URLField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    # درگاه تستی یا تولیدی (mode)
    mode = models.BooleanField(
        default=False, help_text="False برای تست، True برای تولید"
    )
    daily_limit = models.PositiveBigIntegerField(
        default=0, help_text="محدودیت روزانه به ریال"
    )
    monthly_limit = models.PositiveBigIntegerField(
        default=0, help_text="محدودیت ماهانه به ریال"
    )
    webhook_url = models.URLField(
        blank=True, help_text="آدرس وب‌هوک برای اطلاع‌رسانی تراکنش‌ها"
    )
    # حساب بانکی ترجیحی برای تسویه (preferred_bank_account_id در API)
    preferred_bank_account = models.ForeignKey(
        "BankAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_for_terminals",
    )
    is_deleted = models.BooleanField(default=False)
    raw_response = models.JSONField(
        default=dict, help_text="پاسخ کامل API هنگام ثبت درگاه"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["terminal_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.terminal_id}"


class TerminalAllowedDomain(models.Model):
    """
    دامنه‌های مجاز برای درگاه (مطابق API، هر درگاه یک دامنه اصلی دارد ولی اینجا چندتا مجاز است)
    """

    terminal = models.ForeignKey(
        PaymentTerminal, on_delete=models.CASCADE, related_name="allowed_domains"
    )
    domain = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.domain} ({self.terminal})"


class BankAccount(models.Model):
    """
    حساب بانکی مطابق
    """

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        ACTIVE = "active", "فعال"
        REJECTED = "rejected", "رد شده"
        EXPIRED = "expired", "منقضی"
        DELETED = "deleted", "حذف شده"

    class AccountType(models.TextChoices):
        PERSONAL = "personal", "مغازه‌دار"
        SHARE = "share", "تیم"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bank_accounts"
    )
    gateway_account_id = models.CharField(
        max_length=255, unique=True, help_text="شناسه حساب در زرین‌پال (id)"
    )
    iban = models.CharField(max_length=34, unique=True)
    holder_name = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(
        max_length=255, blank=True, help_text="نام بانک صادرکننده"
    )
    bank_slug = models.CharField(
        max_length=100, blank=True, help_text="اسلاگ بانک مثلاً pasargad"
    )
    is_legal = models.BooleanField(default=False, help_text="حساب حقوقی؟")
    type = models.CharField(max_length=30, choices=AccountType.choices)
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PENDING
    )
    is_default = models.BooleanField(default=False)
    raw_response = models.JSONField(default=dict)
    expired_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["iban"]),
            models.Index(fields=["status"]),
        ]
        verbose_name = "حساب بانکی"
        verbose_name_plural = "حساب‌های بانکی"

    def __str__(self):
        return self.iban


class TerminalBankAccount(models.Model):
    """
    اتصال حساب بانکی به درگاه با درصد و اولویت تسویه
    (انعطاف بیشتر نسبت به یک حساب preferred)
    """

    class SettlementType(models.TextChoices):
        PRIMARY = "primary", "اصلی"
        PARTNER = "partner", "شریک"

    terminal = models.ForeignKey(
        PaymentTerminal, on_delete=models.CASCADE, related_name="terminal_bank_accounts"
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="terminal_links"
    )
    settlement_priority = models.PositiveIntegerField(default=1)
    settlement_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=100, help_text="درصد تسویه به این حساب"
    )
    settlement_type = models.CharField(
        max_length=20, choices=SettlementType.choices, default=SettlementType.PRIMARY
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("terminal", "bank_account")]
        ordering = ["settlement_priority"]
        verbose_name = "حساب بانکی درگاه"
        verbose_name_plural = "حساب‌های بانکی درگاه"

    def __str__(self):
        return f"{self.bank_account.iban} -> {self.terminal.terminal_id}"


class Settlement(models.Model):  # برای تسویه حساب

    class Status(models.TextChoices):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        PAID = "paid"
        FAILED = "failed"
        REVERSED = "reversed"

    terminal = models.ForeignKey(PaymentTerminal, on_delete=models.CASCADE)

    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True)

    amount = models.BigIntegerField()

    reference_id = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PENDING
    )

    payable_at = models.DateTimeField()

    reconciled_at = models.DateTimeField(null=True, blank=True)

    raw_response = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
