import logging
import uuid
from datetime import timedelta
from time import perf_counter

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from backend.order import OrderCreateSerializer
from backend.order import Order, OrderItem, OrderStatus, OrderStatusLog
from backend.users.models import User
from backend.wallet.models.models import (IdempotencyKey, PaymentAttempt,
                                          PaymentSession, RefundRequest, Transaction,
                                          Wallet)
from backend.wallet.utils.utils import (check_payment_cooldown, record_payment_failure,
                                        reset_payment_cooldown)
from utils.lock_utils import DistributedLock
from backend.wallet.monitoring import (
    PAYMENT_TOTAL, PAYMENT_SUCCESS, PAYMENT_FAILED, PAYMENT_CANCELED,
    VERIFY_DURATION, GATEWAY_REQUEST_DURATION
)

logger = logging.getLogger(__name__)


class WalletPaymentService:

    def __init__(self, gateway=None):
        self.gateway = gateway

    def calculate_pricing(self, validated_data, request):
        serializer = OrderCreateSerializer(
            data=validated_data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def create_order(self, user, pricing):
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
            subtotal_raw=pricing["subtotal_raw"],
            total_item_discounts=pricing["total_item_discounts"],
            subtotal_after_items=pricing["subtotal_after_items"],
            order_discount_amount=pricing["order_discount_amount"],
            pickup_cost=pricing["pickup_cost"],
            delivery_cost=pricing["delivery_cost"],
            rush_fee=pricing["rush_fee"],
            paid_at=timezone.now(),
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=item["product"],
                    size=item["size"],
                    pricing_tab=item["pricing_tab"],
                    material=item["material_name"],
                    quantity=item["quantity"],
                    price=item["final_item_price"],
                )
                for item in pricing["computed_items"]
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
    # WALLET PAYMENT
    # =====================================================
    def pay_with_wallet(self, *, user, cart, validated_data, request, idempotency_key=None):
        PAYMENT_TOTAL.inc()
        check_payment_cooldown(user.id, "wallet_pay")

        cart_items = list(cart)
        if not cart_items:
            PAYMENT_FAILED.inc()
            record_payment_failure(user.id, "wallet_pay")
            raise ValidationError("سبد خرید خالی است")

        # مدیریت همروندی با قفل توزیع‌شده برای کسر موجودی کاربر
        with DistributedLock(key=f"wallet:pay:{user.id}", timeout=30, blocking_timeout=2):
            if idempotency_key:
                duplicated = IdempotencyKey.objects.filter(
                    key=idempotency_key,
                    user=user,
                    is_processed=True,
                ).first()
                if duplicated:
                    return duplicated.response_data

            pricing = self.calculate_pricing(validated_data, request)
            final_price = pricing["final_price"]

            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=user, is_active=True)

                if wallet.available_balance < final_price:
                    PAYMENT_FAILED.inc()
                    record_payment_failure(user.id, "wallet_pay")
                    raise ValidationError("موجودی کیف پول کافی نیست")

                wallet.available_balance -= final_price
                wallet.save(update_fields=["available_balance"])

                payment = PaymentSession.objects.create(
                    user=user,
                    amount=final_price,
                    type=PaymentSession.Type.wallet,
                    status=PaymentSession.Status.PAID,
                    is_verified=True,
                    paid_at=timezone.now(),
                    verified_at=timezone.now(),
                    payer_ip=self.get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    card_hash="",
                )

                order = self.create_order(user=user, pricing=pricing)
                payment.order = order
                payment.save(update_fields=["order"])

                Transaction.objects.create(
                    wallet=wallet,
                    payment=payment,
                    order=order,
                    amount=final_price,
                    transaction_type=Transaction.TransactionType.PAYMENT,
                    status=Transaction.Status.SUCCESS,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    description="پرداخت سفارش با کیف پول",
                )

                if idempotency_key:
                    IdempotencyKey.objects.create(
                        key=idempotency_key,
                        user=user,
                        endpoint="wallet_payment",
                        request_hash=str(final_price),
                        is_processed=True,
                        response_data={
                            "order_id": order.id,
                            "payment_id": payment.id,
                        },
                    )

                reset_payment_cooldown(user.id, "wallet_pay")
                transaction.on_commit(lambda: cart.clear())
                PAYMENT_SUCCESS.inc()

                logger.info(f"wallet payment success order={order.id}")
                return {
                    "order_id": order.id,
                    "payment_id": payment.id,
                }

    # =========================================================
    # INITIATE WALLET CHARGE
    # =========================================================
    @transaction.atomic
    def initiate_wallet_charge(self, *, user, amount, terminal, callback_url, payer_ip=None):
        PAYMENT_TOTAL.inc()
        check_payment_cooldown(user.id, "wallet_charge")

        payment = PaymentSession.objects.create(
            uuid=uuid.uuid4(),
            user=user,
            terminal=terminal,
            amount=amount,
            type=PaymentSession.Type.gatway,
            payer_ip=payer_ip,
            status=PaymentSession.Status.INITIATED,
            card_hash="",
        )

        PaymentAttempt.objects.create(
            payment=payment,
            authority="",
            status=PaymentAttempt.Status.INITIATED,
            payer_ip=payer_ip,
        )

        gateway_started = perf_counter()
        result = self.gateway.request_payment(
            amount=amount,
            description="شارژ کیف پول",
            mobile=user.phone,
            callback_url=callback_url,
        )
        GATEWAY_REQUEST_DURATION.observe(perf_counter() - gateway_started)

        if not result["success"]:
            PAYMENT_FAILED.inc()
            record_payment_failure(user.id, "wallet_charge")
            payment.status = PaymentSession.Status.FAILED
            payment.response_code = result.get("code")
            payment.fail_reason = result.get("error", "")
            payment.gateway_response = result
            payment.save()

            PaymentAttempt.objects.create(
                payment=payment,
                authority="",
                status=PaymentAttempt.Status.FAILED,
                gateway_response=result,
            )
            raise ValidationError(result.get("error", "خطا در اتصال به درگاه"))

        payment.authority = result["authority"]
        payment.gateway_request = result
        payment.status = PaymentSession.Status.PENDING
        payment.save()

        return {
            "payment_url": result["payment_url"],
            "authority": result["authority"],
            "payment_id": payment.id,
        }

    # =========================================================
    # VERIFY WALLET CHARGE
    # =========================================================
    def verify_wallet_charge(self, *, request, authority, status, callback_payload=None):
        verify_started = perf_counter()
        user = request.user
        payer_ip = request.META.get("REMOTE_ADDR")

        check_payment_cooldown(user.id, "wallet_charge")

        # استفاده از قفل روی شناسه اتوریتی برای جلوگیری از پردازش همزمان وب‌هوک و کاربر
        with DistributedLock(key=f"verify:charge:{authority}", timeout=60, blocking_timeout=1):
            with transaction.atomic():
                payment = (
                    PaymentSession.objects.select_for_update()
                    .filter(authority=authority, user=user)
                    .first()
                )

                if not payment:
                    raise ValidationError("پرداخت پیدا نشد")

                if payment.is_verified:
                    VERIFY_DURATION.observe(perf_counter() - verify_started)
                    return {
                        "success": True,
                        "message": "قبلا تایید شده",
                        "ref_id": payment.ref_id,
                    }

                PaymentAttempt.objects.create(
                    payment=payment,
                    authority=authority,
                    status=PaymentAttempt.Status.CALLBACK_RECEIVED,
                    callback_payload=callback_payload or request.data,
                    payer_ip=payer_ip,
                )

                if status != "OK":
                    PAYMENT_CANCELED.inc()
                    record_payment_failure(user.id, "wallet_charge")
                    payment.status = PaymentSession.Status.CANCELED
                    payment.callback_payload = callback_payload or request.data
                    payment.save()
                    VERIFY_DURATION.observe(perf_counter() - verify_started)
                    return {"success": False, "message": "پرداخت لغو شد"}

                verify_result = self.gateway.verify_payment(
                    authority=authority, amount=payment.amount
                )

                if not verify_result["success"]:
                    PAYMENT_FAILED.inc()
                    record_payment_failure(user.id, "wallet_charge")
                    payment.status = PaymentSession.Status.FAILED
                    payment.response_code = verify_result.get("code")
                    payment.fail_reason = verify_result.get("error")
                    payment.gateway_response = verify_result
                    payment.save()

                    PaymentAttempt.objects.create(
                        payment=payment,
                        authority=authority,
                        status=PaymentAttempt.Status.FAILED,
                        gateway_response=verify_result,
                    )
                    VERIFY_DURATION.observe(perf_counter() - verify_started)
                    raise ValidationError(verify_result.get("error", "verify failed"))

                payment.status = PaymentSession.Status.PAID
                payment.is_verified = True
                payment.ref_id = verify_result["ref_id"]
                payment.response_code = 100
                payment.verified_at = timezone.now()
                payment.paid_at = timezone.now()
                payment.gateway_response = verify_result
                payment.callback_payload = callback_payload or request.data
                payment.save()

                wallet = Wallet.objects.select_for_update().get(user=user, is_active=True)
                wallet.available_balance = F("available_balance") + payment.amount
                # ذخیره ایمن مقدار فیلد F() بدون بروز تداخل همروندی دیتابیس
                wallet.save(update_fields=["available_balance"])
                wallet.refresh_from_db()

                Transaction.objects.create(
                    wallet=wallet,
                    payment=payment,
                    amount=payment.amount,
                    transaction_type=Transaction.TransactionType.DEPOSIT,
                    status=Transaction.Status.SUCCESS,
                    description="شارژ کیف پول",
                )

                PaymentAttempt.objects.create(
                    payment=payment,
                    authority=authority,
                    ref_id=verify_result["ref_id"],
                    status=PaymentAttempt.Status.VERIFIED,
                    gateway_response=verify_result,
                    callback_payload=callback_payload or request.data,
                    payer_ip=payer_ip,
                )

                reset_payment_cooldown(user.id, "wallet_charge")
                PAYMENT_SUCCESS.inc()
                VERIFY_DURATION.observe(perf_counter() - verify_started)

                logger.info(f"wallet charged user={user.id}")
                return {
                    "success": True,
                    "ref_id": verify_result["ref_id"],
                    "amount": payment.amount,
                }

    # =========================================================
    # REFUND TO WALLET
    # =========================================================
    @transaction.atomic
    def refund_to_wallet(self, *, order):
        if order.status != OrderStatus.PAID:
            raise ValidationError("فقط سفارش‌های پرداخت‌شده قابل بازگشت هستند.")

        reason = "لغو سفارش توسط کاربر"
        successful_payment = order.payments.filter(
            status=PaymentSession.Status.PAID
        ).first()

        if not successful_payment:
            raise ValidationError("هیچ پرداخت موفقی برای این سفارش یافت نشد.")
        if successful_payment.amount != order.final_price:
            raise ValidationError("مبلغ سفارش با مبلغ پرداخت تطابق ندارد.")

        wallet = Wallet.objects.select_for_update().get(user=order.user, is_active=True)
        refund_amount = order.final_price

        refund_request = RefundRequest.objects.create(
            user=order.user,
            order=order,
            payment=successful_payment,
            amount=refund_amount,
            reason=reason,
            status=RefundRequest.Status.PROCESSING,
            idempotency_key=uuid.uuid4(),
        )

        wallet.available_balance = F("available_balance") + refund_amount

        if successful_payment.type == PaymentSession.Type.gatway:
            wallet.withdraw_blocked_util = timezone.now() + timedelta(hours=3)
        else:
            wallet.withdraw_blocked_util = None

        wallet.save(update_fields=["available_balance", "withdraw_blocked_util"])
        wallet.refresh_from_db()

        Transaction.objects.create(
            wallet=wallet,
            payment=successful_payment,
            order=order,
            amount=refund_amount,
            transaction_type=Transaction.TransactionType.REFUNDTOWALLET,
            status=Transaction.Status.SUCCESS,
            description=f"بازگشت وجه سفارش {order.id}",
        )

        refund_request.status = RefundRequest.Status.COMPLETED
        refund_request.completed_at = timezone.now()
        refund_request.processed_at = timezone.now()
        refund_request.save(update_fields=["status", "completed_at", "processed_at"])

        order.status = OrderStatus.RETURNED
        order.save(update_fields=["status"])

        system_user, _ = User.objects.get_or_create(
            phone="12345678900", defaults={"fullname": "system"}
        )
        OrderStatusLog.objects.create(
            order=order,
            user=system_user,
            to_status=OrderStatus.RETURNED,
            timestamp=timezone.now(),
        )

        logger.info(f"refund success order={order.id}, amount={refund_amount}")
        return order

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")