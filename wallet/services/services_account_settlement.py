import logging

from django.db import transaction
from django.utils import timezone
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from order.models import *
from wallet.models.setting_payment_models import *

logger = logging.getLogger(__name__)


class ZarinpalSettlementService:
    def __init__(self, gateway_client=None):
        # gateway_client همان کلاسی است که به API زرین‌پال متصل می‌شود
        self.gateway = gateway_client

    @transaction.atomic
    def process_daily_settlement(self, terminal_id):
        """
        محاسبه سهم هر حساب و ثبت درخواست تسویه روزانه
        """
        try:
            terminal = PaymentTerminal.objects.get(id=terminal_id, is_deleted=False)
        except PaymentTerminal.DoesNotExist:
            raise ValidationError("درگاه پرداخت یافت نشد.")

        # دریافت حساب‌های متصل به درگاه به ترتیب اولویت
        terminal_accounts = TerminalBankAccount.objects.filter(
            terminal=terminal, is_active=True
        )

        if not terminal_accounts.exists():
            raise ValidationError("هیچ حساب بانکی فعالی برای این درگاه تعریف نشده است.")

        settlements_created = []
        orders = Order.objects.filter(creat_time=now.timezone().date())
        total_amount = 0
        for order in orders:
            total_amount = total_amount + order.final_price
        for link in terminal_accounts:
            # محاسبه سهم هر حساب (مثلا ۷۰ درصد یا ۳۰ درصد)
            # تبدیل به عدد صحیح (ریال) جهت ارسال به بانک
            share_amount = int((total_amount * link.settlement_percent) / 100)

            if share_amount <= 0:
                continue

            # ۱. ایجاد رکورد تسویه در وضعیت در حال پردازش در دیتابیس خودمان
            settlement = Settlement.objects.create(
                terminal=terminal,
                bank_account=link.bank_account,
                amount=share_amount,
                status=Settlement.Status.IN_PROGRESS,
                payable_at=timezone.now(),
            )

            # ۲. ارسال درخواست تسویه به API زرین‌پال (تسهیم/تسویه)
            # نکته: بسته به متد وب‌سرویس زرین‌پال شما، باید این بخش را هماهنگ کنید
            # معمولاً شناسه حساب در زرین‌پال (gateway_account_id) ارسال می‌شود.
            zarinpal_result = self.gateway.request_settlement(
                account_id=link.bank_account.gateway_account_id,
                amount=share_amount,
                description=f"تسویه روزانه درگاه {terminal.name} - سهم {link.settlement_percent}%",
            )

            if zarinpal_result.get("success"):
                settlement.status = (
                    Settlement.Status.PAID
                )  # یا PENDING تا زمانی که پایا پایا انجام شود
                settlement.reference_id = zarinpal_result.get("reference_id", "")
                settlement.raw_response = zarinpal_result
                settlement.reconciled_at = timezone.now()
                settlement.save(
                    update_fields=[
                        "status",
                        "reference_id",
                        "raw_response",
                        "reconciled_at",
                    ]
                )
                settlements_created.append(settlement)
                logger.info(
                    f"Settlement success for account {link.bank_account.id}: {share_amount} Rials"
                )
            else:
                # در صورت خطا در API زرین‌پال
                settlement.status = Settlement.Status.FAILED
                settlement.raw_response = zarinpal_result
                settlement.save(update_fields=["status", "raw_response"])
                logger.error(
                    f"Settlement failed for account {link.bank_account.id}: {zarinpal_result.get('error')}"
                )

                # بستگی به سیاست کسب‌وکار شما دارد که آیا کل فرآیند Rollback شود یا فقط همین یکی فیلد بخورد.
                # چون متد atomic است، خطا دادن باعث rollback کل درگاه می‌شود.
                raise ValidationError(
                    f"خطا در تسویه زرین‌پال: {zarinpal_result.get('error')}"
                )

        return settlements_created
