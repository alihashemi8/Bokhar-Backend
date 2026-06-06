from rest_framework import serializers


# ==========================================
# ۱. سریالایزرهای حساب بانکی (BankAccount)
# ==========================================
class BankAccountListSerializer(serializers.ModelSerializer):
    """سریالایزر مختصر برای استفاده در لیست‌ها و روابط"""
    class Meta:
        model = BankAccount
        fields = ["id", "iban", "holder_name", "bank_name", "status", "is_default"]


class BankAccountDetailSerializer(serializers.ModelSerializer):
    """سریالایزر کامل برای ثبت و مشاهده جزئیات حساب بانکی"""
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = BankAccount
        fields = "__all__"
        read_only_fields = [
            "status",
            "raw_response",
            "expired_at",
            "deleted_at",
            "created_at",
        ]
# ==========================================
# ۲. سریالایزرهای دامنه‌های مجاز (Allowed Domains)
# ==========================================
class TerminalAllowedDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerminalAllowedDomain
        fields = ["id", "domain", "is_active", "created_at"]
# ==========================================
# ۳. سریالایزرهای اتصال حساب به درگاه (TerminalBankAccount)
# ==========================================
class TerminalBankAccountReadSerializer(serializers.ModelSerializer):
    """نمایش حساب‌های متصل به همراه جزئیات خود حساب بانکی"""
    bank_account = BankAccountListSerializer(read_only=True)
    class Meta:
        model = TerminalBankAccount
        fields = [
            "id",
            "bank_account",
            "settlement_priority",
            "settlement_percent",
            "settlement_type",
            "is_active",
        ]
class TerminalBankAccountWriteSerializer(serializers.ModelSerializer):
    """استفاده برای اتصال یا ویرایش یک حساب به درگاه"""
    class Meta:
        model = TerminalBankAccount
        fields = [
            "bank_account",
            "settlement_priority",
            "settlement_percent",
            "settlement_type",
            "is_active",
        ]

    def validate_bank_account(self, value):
        # 🔒 امنیتی: حساب بانکی حتماً باید متعلق به کاربر لاگین شده باشد
        request = self.context.get('request')
        if request and request.user != value.user:
            raise serializers.ValidationError("این حساب بانکی متعلق به شما نیست و مجاز به استفاده از آن نیستید.")
        return value

    def validate_settlement_percent(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError("درصد تسویه باید بین ۰ تا ۱۰۰ باشد.")
        return value

# ==========================================
# ۴. سریالایزرهای درگاه پرداخت (PaymentTerminal)
# ==========================================
class PaymentTerminalListSerializer(serializers.ModelSerializer):
    """نمایش لیست درگاه‌ها با اطلاعات کلیدی"""
    class Meta:
        model = PaymentTerminal
        fields = ["id", "name", "terminal_id", "status", "mode", "created_at"]
class PaymentTerminalDetailSerializer(serializers.ModelSerializer):
    """نمایش کامل جزئیات درگاه به همراه دامنه‌ها و حساب‌های متصل به آن"""
    owner = serializers.ReadOnlyField(source="owner.phone")
    allowed_domains = TerminalAllowedDomainSerializer(many=True, read_only=True)
    terminal_bank_accounts = TerminalBankAccountReadSerializer(
        many=True, read_only=True
    )
    preferred_bank_account = BankAccountListSerializer(read_only=True)
    class Meta:
        model = PaymentTerminal
        fields = [
            "id",
            "owner",
            "terminal_id",
            "merchant_id",
            "mcc",
            "support_phone",
            "name",
            "logo",
            "status",
            "mode",
            "daily_limit",
            "monthly_limit",
            "webhook_url",
            "preferred_bank_account",
            "allowed_domains",
            "terminal_bank_accounts",
            "created_at",
            "updated_at",
        ]
class PaymentTerminalCreateUpdateSerializer(serializers.ModelSerializer):
    """سریالایزر ساخت و ویرایش درگاه توسط کاربر"""
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = PaymentTerminal
        fields = [
            "owner",
            "merchant_id",
            "mcc",
            "support_phone",
            "name",
            "logo",
            "mode",
            "daily_limit",
            "monthly_limit",
            "webhook_url",
            "preferred_bank_account",
        ]
        read_only_fields = [
            "status",
            "terminal_id",
        ]  # این موارد معمولا پس از پاسخ API زرین‌پال ست می‌شوند

    def validate(self, attrs):
        # بررسی اینکه حساب بانکی ترجیحی متعلق به خود کاربر باشد
        preferred_bank = attrs.get("preferred_bank_account")
        if preferred_bank and preferred_bank.user != attrs["owner"]:
            raise serializers.ValidationError(
                {"preferred_bank_account": "این حساب بانکی متعلق به شما نیست."}
            )
        return attrs
# ==========================================
# ۵. سریالایزر تسویه حساب (Settlement)
# ==========================================
class SettlementSerializer(serializers.ModelSerializer):
    terminal = PaymentTerminalListSerializer(read_only=True)
    bank_account = BankAccountListSerializer(read_only=True)
    class Meta:
        model = Settlement
        fields = [
            "id",
            "terminal",
            "bank_account",
            "amount",
            "reference_id",
            "status",
            "payable_at",
            "reconciled_at",
            "created_at",
        ]
        read_only_fields = [
            "__all__"
        ]  # تسویه حساب‌ها معمولا فقط خواندنی هستند و توسط سیستم صادر می‌شوند
