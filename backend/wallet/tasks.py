from celery import shared_task

from services.services_payment import *
from services.service_zarinpal import *

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)
def process_webhook(
    self,
    event_uuid,
):

    event = WebhookEvent.objects.get(
        uuid=event_uuid
    )

    try:

        event.status = (
            WebhookEvent.Status.PROCESSING
        )

        event.save(
            update_fields=["status"]
        )

        service = PaymentService(
            zarinpal_client=ZarinPalService()
        )

        service.verify_payment(
            authority=event.authority,
            callback_payload=event.payload,
            payer_ip=event.ip_address,
        )

        event.status = (
            WebhookEvent.Status.PROCESSED
        )

        event.processed_at = timezone.now()

        event.save(
            update_fields=[
                "status",
                "processed_at",
            ]
        )

    except Exception as exc:

        event.retry_count += 1

        event.error_message = str(exc)

        event.save(
            update_fields=[
                "retry_count",
                "error_message",
            ]
        )

        raise

from celery import shared_task
from django.utils import timezone
from backend.wallet.models.log_models import WebhookEvent
from backend.wallet.services import WalletPaymentService, ZarinPalService


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)
def process_webhook(self, event_uuid):
    event = WebhookEvent.objects.get(uuid=event_uuid)

    try:
        event.status = WebhookEvent.Status.PROCESSING
        event.save(update_fields=["status"])

        # ساخت نمونه گیت‌وی و سرویس مربوط به عملیات مالی کیف پول
        service = WalletPaymentService(gateway=ZarinPalService())

        # شبیه‌سازی ساختار ماک درخواست کلاینت برای متد کنترل سرویس
        class MockRequest:
            def __init__(self, user, data, ip):
                self.user = user
                self.data = data
                self.META = {"REMOTE_ADDR": ip}

        # فرستادن اطلاعات ذخیره شده در مدل وب‌هوک به عنوان ساختار بدنه تایید نهایی
        mock_request = MockRequest(
            user=event.payment.user, # فرض بر این است رابطه فیلد ریلیشن در دیتابیس برقرار است
            data=event.payload,
            ip=event.ip_address
        )

        service.verify_wallet_charge(
            request=mock_request,
            authority=event.authority,
            status=event.payload.get("Status", "OK"),
            callback_payload=event.payload,
        )

        event.status = WebhookEvent.Status.PROCESSED
        event.processed_at = timezone.now()
        event.save(update_fields=["status", "processed_at"])

    except Exception as exc:
        event.retry_count += 1
        event.error_message = str(exc)
        event.save(update_fields=["retry_count", "error_message"])
        raise