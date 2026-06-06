# =========================================================
"""
class LedgerTransaction(models.Model):

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    payment = models.ForeignKey(
        PaymentSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True

    )

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    #نوع منبع تراکنش
    reference_type = models.CharField(max_length=100)

    reference_id = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["reference_type"]),
            models.Index(fields=["reference_id"]),
        ]


# =========================================================
# LEDGER ENTRY
# =========================================================
class LedgerEntry(models.Model):

    class Side(models.TextChoices):
        DEBIT = "debit"
        CREDIT = "credit"

    transaction = models.ForeignKey(
        LedgerTransaction,
        on_delete=models.CASCADE,
        related_name="entries"
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    side = models.CharField(
        max_length=10,
        choices=Side.choices
    )
    #اسم یا کد حساب مالی
    account_code = models.CharField(max_length=50)

    amount = models.BigIntegerField()

    balance_after = models.BigIntegerField(
        null=True,
        blank=True
    )

    idempotency_key = models.UUIDField(
        unique=True
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ["created_at"]

        indexes = [
            models.Index(fields=["account_code"]),
            models.Index(fields=["side"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):

        if self.pk:
            raise ValidationError(
                "Ledger entries are immutable."
            )

        return super().save(*args, **kwargs)
"""
# =========================================================
# بررسی امکان برداشت از کیف پول
# =========================================================
"""    def can_withdraw(self, user):
        wallet = getattr(user, 'wallet', None)
        if not wallet:
            raise ValidationError("کیف پول برای این کاربر یافت نشد.")

        if wallet.withdraw_blocked_util and timezone.now() < wallet.withdraw_blocked_util:
            raise ValidationError(
                "تا ۳ ساعت پس از بازگشت وجه از درگاه بانکی، برداشت از کیف پول ممکن نیست."
            )
        return True
"""
