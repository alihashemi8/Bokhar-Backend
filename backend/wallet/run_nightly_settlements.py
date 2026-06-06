# wallet/tasks.py
from celery import shared_task
import logging
from backend.wallet.models.setting_payment_models import PaymentTerminal
from backend.wallet.services.service_zarinpal import ZarinPalService
from backend.wallet.services.services_account_settlement import ZarinpalSettlementService

logger = logging.getLogger(__name__)


@shared_task(name="wallet.tasks.run_nightly_settlements")
def run_nightly_settlements():
    """
    تسک خودکار شبانه برای تسویه تمام درگاه‌های فعال سیستم
    """
    logger.info("آغاز فرآیند اتوماتیک تسویه حساب‌های شبانه...")

    active_terminals = PaymentTerminal.objects.filter(status="active", is_deleted=False)

    gateway_client = ZarinPalService()
    settlement_service = ZarinpalSettlementService(gateway_client=gateway_client)

    for terminal in active_terminals:
        try:
            logger.info(f"شروع فرآیند تسویه برای ترمینال {terminal.id} ({terminal.name})")
            settlement_service.process_daily_settlement(terminal_id=terminal.id)
        except Exception as e:
            logger.error(f"خطای بحرانی در تسویه شبانه ترمینال {terminal.id}: {str(e)}", exc_info=True)

    logger.info("فرآیند تسویه شبانه به پایان رسید.")