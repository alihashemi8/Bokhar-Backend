import logging
import uuid

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from order.cart_serializer import OrderCreateSerializer
from order.models import Order, OrderItem, OrderStatus, OrderStatusLog
from order.session import OrderSession
from users.models import *
from wallet.models.models import (PaymentAttempt, PaymentSession,
                                  PaymentTerminal, Transaction, Wallet,
                                  WithdrawalRequest)

from ..utils import (check_payment_cooldown, record_payment_failure,
                     reset_payment_cooldown)

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
        """
        شروع فرآیند پرداخت از طریق درگاه بانکی متصل به سیستم ضد اسپم.
        """
        # کنترل محدودیت تلاش قبل از سنگین شدن پردازش دیتابیس
        check_payment_cooldown(user.id, "gateway_pay")

        cart_items = list(cart)
        if not cart_items:
            record_payment_failure(user.id, "gateway_pay")
            raise ValidationError("سبد خرید خالی است")

        pricing = self._calculate_pricing(validated_data, cart.request)
        terminal = PaymentTerminal.objects.get(id=terminal_id, is_active=True)

        payment = PaymentSession.objects.create(
            user=user,
            terminal=terminal,
            amount=pricing["final_price"],
            type_pay=PaymentSession.Type.GATWAY,  # منطبق بر مدل شما
            status=PaymentSession.Status.INITIATED,
            gateway_request={"pricing_snapshot": pricing},
            card_hash="",  # فیلد اجباری مدل شما
        )

        # ثبت تاریخچه تلاش اولیه کاربر
        PaymentAttempt.objects.create(
            payment=payment,
            authority="",
            status=PaymentAttempt.Status.INITIATED,
        )

        result = self.gateway.request_payment(
            amount=pricing["final_price"],
            description="Order Payment",
            mobile=user.phone,
        )

        if not result["success"]:
            record_payment_failure(user.id, "gateway_pay")
            payment.status = PaymentSession.Status.FAILED
            payment.fail_reason = result.get("error", "درگاه پاسخ نداد")
            payment.save()

            PaymentAttempt.objects.create(
                payment=payment,
                authority="",
                status=PaymentAttempt.Status.FAILED,
                gateway_response=result,
            )
            raise ValidationError(result.get("error", "خطا در اتصال به درگاه"))

        payment.authority = result["authority"]
        payment.gateway_request.update(result)
        payment.status = PaymentSession.Status.PENDING
        payment.save()

        return {
            "url": result["payment_url"],
            "authority": payment.authority,
            "payment_id": payment.id,
        }

    # =====================================================
    # VERIFY GATEWAY PAYMENT (IDEMPOTENT + ORDER CREATION)
    # =====================================================
    @transaction.atomic
    def verify_payment(self, request, authority, status):
        user = request.user

        # کنترل نرخ درخواست‌های ارسالی به بازگشت درگاه برای جلوگیری از Brute Force
        check_payment_cooldown(user.id, "gateway_pay")

        payment = (
            PaymentSession.objects.select_for_update()
            .filter(authority=authority, user=user)
            .first()
        )
        if not payment:
            raise ValidationError("پرداخت پیدا نشد")

        # ---------- IDEMPOTENCY GUARD ----------
        if payment.is_verified:
            return {
                "success": True,
                "message": "قبلاً تأیید شده",
                "order_id": payment.order_id,
            }

        # ثبت دریافت کال‌بک در تاریخچه تلاش‌ها
        PaymentAttempt.objects.create(
            payment=payment,
            authority=authority,
            status=PaymentAttempt.Status.CALLBACK_RECEIVED,
            callback_payload=request.data if hasattr(request, "data") else {},
            payer_ip=self._get_client_ip(request),
        )

        # ---------- CALLBACK REJECTED ----------
        if status != "OK":
            record_payment_failure(user.id, "gateway_pay")
            payment.status = PaymentSession.Status.CANCELED
            payment.callback_payload = request.data if hasattr(request, "data") else {}
            payment.save()
            return {"success": False, "message": "پرداخت توسط کاربر لغو شد"}

        # ---------- GATEWAY VERIFY ----------
        verify_result = self.gateway.verify_payment(authority, payment.amount)
        if not verify_result["success"]:
            record_payment_failure(user.id, "gateway_pay")
            payment.status = PaymentSession.Status.FAILED
            payment.fail_reason = verify_result.get("error", "خطای تأیید تراکنش")
            payment.verify_response = verify_result
            payment.save()

            PaymentAttempt.objects.create(
                payment=payment,
                authority=authority,
                status=PaymentAttempt.Status.FAILED,
                gateway_response=verify_result,
            )
            raise ValidationError(verify_result.get("error", "تأیید پرداخت ناموفق بود"))

        # ---------- MARK AS PAID ----------
        payment.status = PaymentSession.Status.PAID  # منطبق با Status.choices مدل شما
        payment.is_verified = True
        payment.ref_id = verify_result["ref_id"]
        payment.paid_at = timezone.now()
        payment.verified_at = timezone.now()
        payment.verify_response = verify_result
        payment.callback_payload = request.data if hasattr(request, "data") else {}

        pricing = payment.gateway_request.get("pricing_snapshot")

        # ---------- IDEMPOTENT ORDER CREATION ----------
        if not payment.order_id:
            order = self._create_order(user, pricing)
            payment.order = order
        payment.save()

        # ---------- WALLET TRANSACTION ----------
        wallet, created = Wallet.objects.get_or_create(
            user=user, defaults={"is_active": True}
        )
        wallet = Wallet.objects.select_for_update().get(id=wallet.id)

        # ثبت تاریخچه تراکنش کیف‌پول پلتفرم
        Transaction.objects.create(
            wallet=wallet,
            payment=payment,
            order=payment.order,
            amount=payment.amount,
            transaction_type=Transaction.TransactionType.PAYMENT,
            status=Transaction.Status.SUCCESS,
            description="پرداخت سفارش از درگاه",
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # ثبت موفقیت نهایی در لاگ تلاش‌ها
        PaymentAttempt.objects.create(
            payment=payment,
            authority=authority,
            ref_id=verify_result["ref_id"],
            status=PaymentAttempt.Status.VERIFIED,
            gateway_response=verify_result,
            payer_ip=self._get_client_ip(request),
        )

        # خروج موفقیت‌آمیز -> ریست محدودیت تلاش‌ها
        reset_payment_cooldown(user.id, "gateway_pay")

        # خالی کردن سبد خرید کاربر
        OrderSession(request).clear()

        return {
            "success": True,
            "order_id": payment.order.id,
            "ref_id": payment.ref_id,
            "payment_id": payment.id,
        }

    # =====================================================
    # WITHDRAW FROM WALLET TO BANK ACCOUNT (با محدودیت ۳ ساعته)
    # =====================================================
    @transaction.atomic
    def withdraw_to_bank(
        self, *, user, amount, deposit_payment_uuid, method, request=None
    ):
        """
        برداشت موجودی کیف پول از طریق استرداد زرین‌پال به کارت شارژکننده.
        پارامترها:
            user: کاربر
            amount: مبلغ برداشت (ریال)
            deposit_payment_uuid: شناسه PaymentSession که باید به آن استرداد شود
            method: CARD یا PAYA
            request: شیء HttpRequest (اختیاری)
        """
        # احراز هویت اولیه (در صورت نیاز کد مربوط به cooldown و ...)
        check_payment_cooldown(user.id, "withdraw")

        # قفل کردن کیف پول برای جلوگیری از تداخل
        wallet = Wallet.objects.select_for_update().get(user=user, is_active=True)

        # اعتبارسنجی موجودی
        if wallet.available_balance < amount:
            record_payment_failure(user.id, "withdraw")
            raise ValidationError("موجودی کیف پول کافی نیست")

        # بررسی محدودیت زمانی برداشت (در صورت نیاز)
        if not self.validate_withdrawal_eligibility(user):
            record_payment_failure(user.id, "withdraw")
            raise ValidationError(
                "برداشت از کیف پول تا ۳ ساعت پس از بازگشت وجه از درگاه بانکی امکان‌پذیر نیست."
            )

        # دریافت تراکنش شارژ اصلی
        try:
            deposit_payment = PaymentSession.objects.get(
                uuid=deposit_payment_uuid,
                user=user,
                status=PaymentSession.Status.PAID,
                type_pay=PaymentSession.Type.WALLET,  # فقط تراکنش‌های شارژ کیف پول
            )
        except PaymentSession.DoesNotExist:
            raise ValidationError("تراکنش شارژ معتبری یافت نشد.")

        # مبلغ درخواستی نباید از مبلغ تراکنش اصلی بیشتر باشد
        if amount > deposit_payment.amount:
            raise ValidationError(
                "مبلغ برداشت نمی‌تواند از مبلغ تراکنش شارژ اصلی بیشتر باشد."
            )

        # کسر موقت از کیف پول
        wallet.available_balance = F("available_balance") - amount
        wallet.save(update_fields=["available_balance"])
        wallet.refresh_from_db()

        # ایجاد درخواست برداشت
        withdrawal = WithdrawalRequest.objects.create(
            user=user,
            wallet=wallet,
            amount=amount,
            deposit_payment=deposit_payment,
            method=method,
            bank_name="",  # یا می‌توان از اطلاعات کارت استخراج کرد
            status=WithdrawalRequest.Status.PENDING,
            idempotency_key=uuid.uuid4(),
        )

        # ثبت تراکنش مالی (در انتظار)
        txn = Transaction.objects.create(
            wallet=wallet,
            payment=deposit_payment,  # ارجاع به تراکنش اصلی
            amount=amount,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            status=Transaction.Status.PENDING,
            description=f"برداشت به کارت {deposit_payment.card_pan}",
            ip_address=self._get_client_ip(request) if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
        )

        # فراخوانی سرویس استرداد زرین‌پال
        refund_result = self.gateway.request_refund(
            session_id=deposit_payment.authority,
            amount=amount,
            description=f"برداشت کیف پول کاربر {user.id}",
            method=method,  # CARD یا PAYA
        )

        if refund_result["success"]:
            # موفقیت‌آمیز
            withdrawal.status = WithdrawalRequest.Status.COMPLETED
            withdrawal.processed_at = timezone.now()
            withdrawal.save(update_fields=["status", "processed_at"])

            txn.status = Transaction.Status.SUCCESS
            txn.save(update_fields=["status"])

            # رفرش نهایی کیف پول (اختیاری، چون کسر قبلاً انجام شده)
            # wallet.refresh_from_db()

            reset_payment_cooldown(user.id, "withdraw")
            logger.info(
                f"withdrawal success user={user.id}, amount={amount}, ref_id={refund_result.get('refund_id')}"
            )
            return {
                "withdrawal_id": withdrawal.uuid,
                "amount": amount,
                "new_balance": wallet.available_balance,
                "refund_id": refund_result.get("refund_id"),
            }
        else:
            # شکست در استرداد: برگرداندن وجه به کیف پول
            wallet.available_balance = F("available_balance") + amount
            wallet.save(update_fields=["available_balance"])
            wallet.refresh_from_db()

            withdrawal.status = WithdrawalRequest.Status.FAILED
            withdrawal.failure_reason = refund_result.get("error", "خطای ناشناخته")
            withdrawal.save(update_fields=["status", "failure_reason"])

            txn.status = Transaction.Status.FAILED
            txn.save(update_fields=["status"])

            # record_payment_failure(user.id, "withdraw")
            logger.error(
                f"withdrawal failed user={user.id}, reason={refund_result.get('error')}"
            )
            raise ValidationError(refund_result.get("error", "خطا در استرداد وجه"))

    # =====================================================
    # VALIDATION HELPER FOR WITHDRAWAL (برای استفاده در ویوها)
    # =====================================================
    def validate_withdrawal_eligibility(self, user):
        """
        بررسی وضعیت قفل کیف پول پیش از رندر کردن فرم‌های برداشت وجه.
        """
        wallet = getattr(user, "wallet", None)
        if not wallet or not wallet.is_active:
            raise ValidationError("کیف پول فعال برای شما یافت نشد.")

        if (
            wallet.withdraw_blocked_util
            and timezone.now() < wallet.withdraw_blocked_util
        ):
            remaining = wallet.withdraw_blocked_util - timezone.now()
            hours = remaining.total_seconds() / 3600
            raise ValidationError(f"برداشت تا {hours:.1f} ساعت دیگر امکان‌پذیر نیست.")
        return True


# بعد وریفای درخواست
