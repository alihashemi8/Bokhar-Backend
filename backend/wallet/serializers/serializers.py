from rest_framework import serializers

from backend.order import Order
from backend.wallet.models.models import RefundRequest, Transaction, WithdrawalRequest


# =========================================================
# 1. Payment Create (درگاه بانکی)
# =========================================================
class PaymentCreateSerializer(serializers.Serializer):
    terminal_id = serializers.IntegerField(help_text="شناسه ترمینال پرداخت فعال")

    # در صورتی که آدرس یا اقلام سبد خرید مستقیماً در درگاه نیاز به ارسال دارند،
    # می‌توانید فیلدهای زیر را از کامنت خارج کنید:
    # address_id = serializers.IntegerField(required=True)
    # description = serializers.CharField(required=False, allow_blank=True)
# =========================================================
# 2. Payment Verify (کال‌بک درگاه)
# =========================================================
class PaymentVerifySerializer(serializers.Serializer):
    authority = serializers.CharField(
        max_length=255, help_text="شناسه خرید ارسالی از زرین‌پال"
    )
    status = serializers.CharField(
        max_length=30, help_text="وضعیت ارسالی از کال‌بک درگاه"
    )
    amount = serializers.IntegerField(
        required=False, help_text="مبلغ تراکنش جهت تطابق امنیتی بیشتر"
    )

    def validate_status(self, value):
        # تبدیل به حروف بزرگ برای جلوگیری از حساسیت به حروف کوچک و بزرگ در ساختار URL
        normalized_value = value.upper()
        if normalized_value not in ["OK", "NOK"]:
            raise serializers.ValidationError(
                "وضعیت ارسالی از درگاه نامعتبر است (باید OK یا NOK باشد)."
            )
        return normalized_value


# =========================================================
# 3. Refund Request (درخواست بازگشت وجه سفارش)
# =========================================================
class RefundRequestSerializer(serializers.ModelSerializer):
    # استفاده از PrimaryKeyRelatedField برای تطابق کامل با فیلد order در مدل
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), write_only=True
    )

    class Meta:
        model = RefundRequest
        fields = [
            "order",
            "amount",
            "reason",
        ]

    def validate(self, attrs):
        order = attrs.get("order")
        amount = attrs.get("amount")

        # ۱. بررسی اینکه سفارش حتماً پرداخت شده باشد تا امکان ریفاند وجود داشته باشد
        # توجه: نام OrderStatus.PAID را بر اساس الگوهای متداول خود سفارش مطابقت دهید.
        if order.status != "paid":
            raise serializers.ValidationError(
                {
                    "order": "تنها برای سفارش‌های پرداخت شده می‌توان درخواست بازگشت وجه ثبت کرد."
                }
            )

        # ۲. اعتبارسنجی مبلغ ریفاند (نباید بیشتر از مبلغ پرداختی سفارش باشد)
        # فرض بر این است که مدل Order فیلدی به نام final_price یا مبلغ پرداختی دارد.
        if hasattr(order, "final_price") and amount > order.final_price:
            raise serializers.ValidationError(
                {
                    "amount": "مبلغ درخواستی برای بازگشت وجه نمی‌تواند بیشتر از مبلغ سفارش باشد."
                }
            )

        return attrs


# =========================================================
# 4. Withdrawal Request (برداشت از کیف پول به بانک)
# =========================================================
class WithdrawalRequestSerializer(serializers.ModelSerializer):
    # در سریالایزر:
    deposit_payment_uuid = serializers.UUIDField(required=True, write_only=True)
    method = serializers.ChoiceField(
        choices=WithdrawalRequest.Method.choices, default=WithdrawalRequest.Method.CARD
    )

    class Meta:
        model = WithdrawalRequest
        fields = ["amount", "bank_name", "method", "deposit_payment_uuid"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "مبلغ درخواست برداشت باید بزرگتر از صفر باشد."
            )
        return value


# =========================================================
# 5. Wallet Charge (شارژ کیف پول از درگاه)
# =========================================================
class WalletChargeSerializer(serializers.Serializer):
    # تنظیم حداقل مبلغ بر اساس واحد پولی سیستم شما (تومان/ریال)
    amount = serializers.IntegerField(
        min_value=100000,
        max_value=10000000,
        error_messages={
            "min_value": "حداقل مبلغ جهت شارژ کیف پول 100000 واحد می‌باشد و حداکثر مقدار 10000000 است."
        },
    )


# =========================================================
# 6. Transaction History (نمایش تراکنش‌های کیف پول)
# =========================================================
class TransactionSerializer(serializers.ModelSerializer):
    # برای نمایش خوانا و متنی وضعیت و نوع تراکنش بجای کلیدهای دیتابیسی
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "uuid",
            "trace_id",
            "amount",
            "transaction_type",
            "transaction_type_display",
            "status",
            "status_display",
            "description",
            "created_at",
        ]
        read_only_fields = fields
