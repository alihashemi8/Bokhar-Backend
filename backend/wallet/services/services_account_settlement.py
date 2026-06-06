import logging
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from backend.order import Order
from backend.wallet.models.setting_payment_models import PaymentTerminal, TerminalBankAccount, Settlement

logger = logging.getLogger(__name__)


class ZarinpalSettlementService:
    def __init__(self, gateway_client):
        self.gateway = gateway_client

    def process_daily_settlement(self, terminal_id):
        """
        محاسبه سهم هر حساب و ثبت درخواست تسویه روزانه به صورت کاملاً امن
        """
        try:
            terminal = PaymentTerminal.objects.get(id=terminal_id, is_deleted=False)
        except PaymentTerminal.DoesNotExist:
            raise ValidationError("درگاه پرداخت یافت نشد.")

        # ۱. دریافت حساب‌های متصل به درگاه به ترتیب اولویت
        terminal_accounts = TerminalBankAccount.objects.filter(
            terminal=terminal, is_active=True
        ).select_related('bank_account')

        if not terminal_accounts.exists():
            raise ValidationError("هیچ حساب بانکی فعالی برای این درگاه تعریف نشده است.")

        # بررسی اینکه مجموع درصدها دقیقاً ۱۰۰ باشد
        total_percent = sum(link.settlement_percent for link in terminal_accounts)
        if total_percent != 100:
            raise ValidationError(f"مجموع درصدهای تسویه حساب‌های فعال باید ۱۰۰ باشد. درصد فعلی: {total_percent}")

        # ۲. محاسبه سهم از سفارش‌های "پرداخت شده" امروز
        today = timezone.now().date()

        # ⚠️ مهم: فقط سفارش‌هایی که پرداخت آن‌ها موفق بوده (مثلاً status='paid') باید تسویه شوند
        orders = Order.objects.filter(
            created_at__date=today,  # فرض بر اینکه نام فیلد شما یا created_at است یا طبق مدل قبلی اصلاح شده
            status="paid"  # حتماً وضعیت سفارش‌های موفق را فیلتر کنید
        )

        total_amount = sum(order.final_price for order in orders)
        if total_amount <= 0:
            logger.info(f"مبلغی برای تسویه درگاه {terminal_id} در تاریخ {today} وجود ندارد.")
            return []

        settlements_created = []

        # فرآیند پردازش تک تک حساب‌ها
        for link in terminal_accounts:
            share_amount = int((Decimal(total_amount) * link.settlement_percent) / 100)

            if share_amount <= 0:
                continue

            # استفاده از ساختار اتمیک مجزا برای هر رکورد تسویه تا خطای یک حساب، بقیه را خراب نکند
            with transaction.atomic():
                # جلوگیری از دبل سابمیت یا تسویه تکراری برای یک حساب در یک روز خاص
                already_settled = Settlement.objects.filter(
                    terminal=terminal,
                    bank_account=link.bank_account,
                    created_at__date=today,
                    status__in=[Settlement.Status.IN_PROGRESS, Settlement.Status.PAID]
                ).exists()

                if already_settled:
                    logger.warning(f"تسویه برای حساب {link.bank_account.id} امروز قبلاً انجام شده است.")
                    continue

                # ایجاد رکورد اولیه
                settlement = Settlement.objects.create(
                    terminal=terminal,
                    bank_account=link.bank_account,
                    amount=share_amount,
                    status=Settlement.Status.PENDING,
                    payable_at=timezone.now(),
                )

                # ارسال درخواست به API زرین‌پال
                # در این بخش معمولاً شبا یا gateway_account_id ارسال می‌شود.
                zarinpal_result = self.gateway.request_settlement(
                    account_id=link.bank_account.gateway_account_id or link.bank_account.iban,
                    amount=share_amount,
                    description=f"تسویه روزانه درگاه {terminal.name} - سهم {link.settlement_percent}%",
                )

                if zarinpal_result.get("success"):
                    settlement.status = Settlement.Status.IN_PROGRESS  # در انتظار سیکل پایا بانک
                    settlement.reference_id = zarinpal_result.get("reference_id", "")
                    settlement.raw_response = zarinpal_result
                    settlement.reconciled_at = timezone.now()
                    settlement.save()
                    settlements_created.append(settlement)
                    logger.info(f"درخواست تسویه با موفقیت ثبت شد: {share_amount} ریال برای حساب {link.bank_account.id}")
                else:
                    settlement.status = Settlement.Status.FAILED
                    settlement.raw_response = zarinpal_result
                    settlement.save()
                    logger.error(f"خطا در تسویه حساب {link.bank_account.id}: {zarinpal_result.get('error')}")

        return settlements_created