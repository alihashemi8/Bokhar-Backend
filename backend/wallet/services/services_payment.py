import logging
from time import perf_counter
from django.db import transaction
from rest_framework.exceptions import ValidationError

from backend.order import OrderCreateSerializer
from backend.order import Order, OrderItem, OrderStatus, OrderStatusLog
from backend.wallet.utils.utils import (check_payment_cooldown, record_payment_failure,
                                        reset_payment_cooldown)

# ۱. اصلاح آدرس‌دهی ماژول متریک‌ها بر اساس فایل ارسالی شما
from backend.wallet.monitoring import (
    PAYMENT_TOTAL, PAYMENT_SUCCESS, PAYMENT_FAILED, VERIFY_DURATION, GATEWAY_REQUEST_DURATION
)
from ..utils.lock_utils import DistributedLock
from service_helper import create_audit_log

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(self, zarinpal_client):
        self.gateway = zarinpal_client

    # =====================================================
    # HELPER: Get Client IP
    # =====================================================
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    # =====================================================
    # PRICING SNAPSHOT (NO RECALC IN VERIFY)
    # =====================================================
    def _calculate_pricing(self, validated_data, request):
        serializer = OrderCreateSerializer(
            data=validated_data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    # =====================================================
    # IDEMPOTENT ORDER CREATION
    # =====================================================
    def _create_order(self, user, pricing):
        order = Order.objects.create(
            user=user,
            address=pricing["address"],
            pickup_date=pricing["pickup_date"],
            pickup_shift=pricing["pickup_shift"],
            delivery_date=pricing["delivery_date"],
            delivery_shift=pricing["delivery_shift"],
            description=pricing.get("description", ""),
            status=OrderStatus.PAID,
            final_price=pricing["final_price"],
            paid_at=timezone.now(),
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=i["product"],
                    size=i["size"],
                    pricing_tab=i["pricing_tab"],
                    material=i["material_name"],
                    quantity=i["quantity"],
                    price=i["final_item_price"],
                )
                for i in pricing["computed_items"]
            ]
        )

        system_user, _ = User.objects.get_or_create(
            phone="12345678900", defaults={"fullname": "system"}
        )
        OrderStatusLog.objects.create(
            order=order,
            user=system_user,
            to_status=OrderStatus.PAID,
            timestamp=timezone.now(),
        )
        return order

    # =====================================================
    # INITIATE GATEWAY PAYMENT
    # =====================================================
    @transaction.atomic
    def initiate_payment(self, user, cart, validated_data, terminal_id):
        PAYMENT_TOTAL.inc()
        check_payment_cooldown(user.id, "gateway_pay")

        cart_items = list(cart)
        if not cart_items:
            PAYMENT_FAILED.inc()
            record_payment_failure(user.id, "gateway_pay")
            raise ValidationError("سبد خرید خالی است")

        serializer = OrderCreateSerializer(
            data=validated_data,
            context={"request": cart.request}
        )
        serializer.is_valid(raise_exception=True)
        pricing = serializer.save()

        terminal = PaymentTerminal.objects.get(id=terminal_id, is_active=True)

        payment = PaymentSession.objects.create(
            user=user,
            terminal=terminal,
            amount=pricing["final_price"],
            type_pay=PaymentSession.Type.GATEWAY,
            status=PaymentSession.Status.INITIATED,
            gateway_request={"pricing_snapshot": pricing},
            card_hash="",
        )

        create_audit_log(
            action="PAYMENT_INITIATED",
            user=user,
            payment=payment,
            new_data={"amount": payment.amount, "status": payment.status},
        )

        gateway_started = perf_counter()
        result = self.gateway.request_payment(
            amount=payment.amount,
            description="Order Payment",
            mobile=user.phone,
        )
        GATEWAY_REQUEST_DURATION.observe(perf_counter() - gateway_started)

        if not result["success"]:
            PAYMENT_FAILED.inc()
            payment.status = PaymentSession.Status.FAILED
            payment.fail_reason = result.get("error", "gateway error")
            payment.save()
            raise ValidationError(result["error"])

        payment.authority = result["authority"]
        payment.gateway_response = result
        payment.status = PaymentSession.Status.PENDING
        payment.save(update_fields=["authority", "gateway_response", "status"])
        PAYMENT_SUCCESS.inc()

        return {
            "url": result["payment_url"],
            "authority": payment.authority,
            "payment_id": payment.id,
        }

    # =====================================================
    # VERIFY GATEWAY PAYMENT (IDEMPOTENT + ORDER CREATION)
    # =====================================================
    def verify_payment(self, *, authority, callback_payload=None, payer_ip=None):
        verify_started = perf_counter()

        # ۲. استفاده بهینه از قابلیت Context Manager قفل توزیع‌شده با ساختار with
        # این کار ریسک Deadlock را صفر کرده و نیازی به بلوک try/finally و کدهای اضافه ندارد.
        with DistributedLock(key=f"verify:{authority}", timeout=60, blocking_timeout=1):
            with transaction.atomic():
                payment = PaymentSession.objects.select_for_update().filter(authority=authority).first()

                if not payment:
                    raise ValidationError("Payment not found.")

                if payment.is_verified:
                    VERIFY_DURATION.observe(perf_counter() - verify_started)
                    return {
                        "success": True,
                        "message": "already verified",
                        "order_id": payment.order_id,
                        "ref_id": payment.ref_id,
                    }

                verify_result = self.gateway.verify_payment(
                    authority=authority,
                    amount=payment.amount,
                )
                payment.verify_response = verify_result

                if not verify_result["success"]:
                    PAYMENT_FAILED.inc()
                    payment.status = PaymentSession.Status.FAILED
                    payment.save(update_fields=["status", "verify_response"])

                    create_audit_log(
                        action="PAYMENT_FAILED",
                        user=payment.user,
                        payment=payment,
                        new_data={"status": payment.status},
                        ip=payer_ip,
                    )
                    VERIFY_DURATION.observe(perf_counter() - verify_started)
                    return {"success": False}

                payment.refresh_from_db()
                if payment.is_verified:
                    VERIFY_DURATION.observe(perf_counter() - verify_started)
                    return {
                        "success": True,
                        "message": "already verified",
                        "order_id": payment.order_id,
                        "ref_id": payment.ref_id,
                    }

                PAYMENT_SUCCESS.inc()
                payment.status = PaymentSession.Status.PAID
                payment.is_verified = True
                payment.ref_id = verify_result["ref_id"]
                payment.callback_payload = callback_payload or {}
                payment.payer_ip = payer_ip
                payment.paid_at = timezone.now()
                payment.verified_at = timezone.now()

                if not payment.order_id:
                    pricing = payment.gateway_request.get("pricing_snapshot")
                    order = self._create_order(payment.user, pricing)
                    payment.order = order

                payment.save()

                wallet, _ = Wallet.objects.get_or_create(
                    user=payment.user,
                    defaults={"is_active": True}
                )

                Transaction.objects.get_or_create(
                    payment=payment,
                    transaction_type=Transaction.TransactionType.PAYMENT,
                    defaults={
                        "wallet": wallet,
                        "order": payment.order,
                        "amount": payment.amount,
                        "status": Transaction.Status.SUCCESS,
                    }
                )

                # ۳. رفع خطای سینتکسی (Indentation Error) و کامای غایب در ساخت آبجکت تمپت
                PaymentAttempt.objects.create(
                    payment=payment,
                    authority=authority,
                    status=PaymentAttempt.Status.VERIFIED,
                    ref_id=payment.ref_id,
                    callback_payload=callback_payload or {},
                    payer_ip=payer_ip,
                    gateway_response=verify_result,
                )

                create_audit_log(
                    action="PAYMENT_VERIFIED",
                    user=payment.user,
                    payment=payment,
                    new_data={
                        "status": payment.status,
                        "ref_id": payment.ref_id,
                        "order_id": payment.order_id,
                    },
                    ip=payer_ip,
                )

                reset_payment_cooldown(payment.user_id, "gateway_pay")
                VERIFY_DURATION.observe(perf_counter() - verify_started)

                return {
                    "success": True,
                    "order_id": payment.order_id,
                    "ref_id": payment.ref_id,
                }

    # =====================================================
    # WITHDRAW FROM WALLET TO BANK ACCOUNT
    # =====================================================
    @transaction.atomic
    def withdraw_to_bank(self, *, user, amount, deposit_payment_uuid, method, request=None):
        # از شمارنده‌های پرومتئوس که بالاتر ایمپورت شدند استفاده می‌شود
        # برای بخش withdraw شمارنده‌ای در فایل مانیتورینگ شما تعریف نشده بود، در صورت نیاز می‌توانید به آن اضافه کنید
        check_payment_cooldown(user.id, "withdraw")

        wallet = Wallet.objects.select_for_update().get(user=user, is_active=True)

        if wallet.available_balance < amount:
            record_payment_failure(user.id, "withdraw")
            raise ValidationError("موجودی کافی نیست")

        if not self.validate_withdrawal_eligibility(user):
            raise ValidationError("برداشت موقتاً غیر فعال است")

        deposit_payment = PaymentSession.objects.get(
            uuid=deposit_payment_uuid,
            user=user,
            status=PaymentSession.Status.PAID,
        )

        if amount > deposit_payment.amount:
            raise ValidationError("مبلغ درخواستی بیشتر از تراکنش مرجع است")

        wallet.available_balance -= amount
        wallet.save()

        withdrawal = WithdrawalRequest.objects.create(
            user=user,
            wallet=wallet,
            amount=amount,
            deposit_payment=deposit_payment,
            method=method,
            status=WithdrawalRequest.Status.PENDING,
        )

        txn = Transaction.objects.create(
            wallet=wallet,
            payment=deposit_payment,
            amount=amount,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            status=Transaction.Status.PENDING,
        )

        refund_result = self.gateway.request_refund(
            session_id=deposit_payment.authority,
            amount=amount,
            method=method,
        )

        if refund_result["success"]:
            withdrawal.status = WithdrawalRequest.Status.COMPLETED
            withdrawal.save(update_fields=["status"])

            txn.status = Transaction.Status.SUCCESS
            txn.save(update_fields=["status"])

            return {"success": True}

        # با بروز خطا، خط پایین اتمیک عمل کرده و کل دیتابیس (جمله کسر موجودی) را رول‌بک می‌کند.
        raise ValidationError("عملیات استرداد وجه از طریق درگاه با خطا مواجه شد.")

    # =====================================================
    # VALIDATION HELPER FOR WITHDRAWAL
    # =====================================================
    def validate_withdrawal_eligibility(self, user):
        wallet = getattr(user, "wallet", None)
        if not wallet or not wallet.is_active:
            raise ValidationError("کیف پول فعال برای شما یافت نشد.")

        if wallet.withdraw_blocked_util and timezone.now() < wallet.withdraw_blocked_util:
            remaining = wallet.withdraw_blocked_util - timezone.now()
            hours = remaining.total_seconds() / 3600
            raise ValidationError(f"برداشت تا {hours:.1f} ساعت دیگر امکان‌پذیر نیست.")
        return True