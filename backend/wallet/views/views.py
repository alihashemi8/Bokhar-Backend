# Create your views here.

from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from backend.wallet.models.models import Order
from backend.wallet.services import WalletPaymentService, ZarinPalService
from backend.wallet.serializers import WalletChargeSerializer, PaymentVerifySerializer  # ایمپورت لایه‌های سریالایزر شما
from backend.order import OrderSession  # آدرس ماژول سبد خرید شما


class WalletPayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = OrderSession(request)
        user = request.user
        data = request.data
        idempotency_key = request.data.get("idempotency_key")

        service = WalletPaymentService(gateway=ZarinPalService())
        try:
            result = service.pay_with_wallet(
                user=user,
                cart=cart,
                validated_data=data,
                request=request,
                idempotency_key=idempotency_key,
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WalletChargeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        terminal_id = request.data.get("terminal_id")
        if not terminal_id:
            return Response(
                {"detail": "شناسه ترمینال الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            terminal = PaymentTerminal.objects.get(id=terminal_id, is_active=True)
        except PaymentTerminal.DoesNotExist:
            return Response(
                {"detail": "ترمینال معتبری یافت نشد."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        callback_url = request.build_absolute_uri(reverse("payment-verify"))
        payer_ip = request.META.get("REMOTE_ADDR")

        service = WalletPaymentService(gateway=ZarinPalService())
        try:
            result = service.initiate_wallet_charge(
                user=request.user,
                amount=amount,
                terminal=terminal,
                callback_url=callback_url,
                payer_ip=payer_ip,
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VeryfiChargeWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        authority = serializer.validated_data["authority"]
        payment_status = serializer.validated_data["status"]

        service = WalletPaymentService(gateway=ZarinPalService())
        try:
            result = service.verify_wallet_charge(
                request=request,
                authority=authority,
                status=payment_status,
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RefundOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            # بررسی کوچک کردن وضعیت رشته برای تطابق دقیق فیلد استاتوس دیتابیس
            order = Order.objects.get(id=id, status=OrderStatus.PAID)
        except Order.DoesNotExist:
            return Response(
                {"detail": "سفارش پرداخت‌شده‌ای یافت نشد."}, status=status.HTTP_404_NOT_FOUND
            )

        service = WalletPaymentService(gateway=ZarinPalService())
        try:
            updated_order = service.refund_to_wallet(order=order)
            return Response(
                {
                    "detail": "بازگشت وجه با موفقیت به کیف پول شما واریز شد.",
                    "order_id": updated_order.id,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


import hashlib
from uuid import UUID
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

# آدرس آبجکت سبد خرید شما
from backend.wallet.services.services_payment import PaymentService  # سرویس‌های اصلاح شده


class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response(
                {"detail": "Idempotency-Key header is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            UUID(idempotency_key)
        except ValueError:
            return Response(
                {"detail": "Invalid Idempotency-Key format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_hash = hashlib.sha256(
            json.dumps(request.data, sort_keys=True).encode()
        ).hexdigest()

        # استفاده امن از ساختار کنترل همروندی توزیع‌شده برای یک کاربر خاص
        with DistributedLock(key=f"payment:initiate:{request.user.id}", timeout=60, blocking_timeout=1):

            with transaction.atomic():
                existing = (
                    IdempotencyKey.objects
                    .select_for_update()
                    .filter(
                        key=idempotency_key,
                        user=request.user,
                        endpoint=request.path,
                    )
                    .first()
                )

                if existing:
                    if existing.request_hash != request_hash:
                        return Response(
                            {"detail": "This Idempotency-Key has already been used with different data."},
                            status=status.HTTP_409_CONFLICT,
                        )

                    if existing.is_processed:
                        return Response(existing.response_data, status=existing.response_status)
                    else:
                        # اگر رکورد وجود دارد ولی پردازش آن تمام نشده، یعنی درخواست موازی همزمان آمده است
                        return Response(
                            {"detail": "A request with this Idempotency-Key is already in progress."},
                            status=status.HTTP_409_CONFLICT
                        )

                # ایجاد وضعیت موقت در حالت در حال پردازش
                existing = IdempotencyKey.objects.create(
                    key=idempotency_key,
                    user=request.user,
                    endpoint=request.path,
                    request_hash=request_hash,
                    is_processed=False,
                )

            try:
                cart = OrderSession(request)
                terminal_id = serializer.validated_data["terminal_id"]

                service = PaymentService(zarinpal_client=ZarinPalService())
                result = service.initiate_payment(
                    user=request.user,
                    cart=cart,
                    validated_data=serializer.validated_data,
                    terminal_id=terminal_id,
                )

                # ذخیره پاسخ موفق در Idempotency برای دفعات بعدی ریترای
                existing.response_status = status.HTTP_200_OK
                existing.response_data = result
                existing.is_processed = True
                existing.save(update_fields=["response_status", "response_data", "is_processed"])

                return Response(result, status=status.HTTP_200_OK)

            except Exception as exc:
                # اصلاح باگ حیاتی: در صورت خطا، رکورد آیدمپوتنسی را پاک می‌کنیم
                # تا کاربر بتواند بعد از رفع مشکل مجدداً با همین کلید تلاش کند.
                existing.delete()
                raise


from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated

class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        authority = serializer.validated_data["authority"]
        # دریافت IP کاربر جهت ذخیره در تاریخچه لاگ‌های امنیتی پرداخت
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        payer_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR", "")

        service = PaymentService(zarinpal_client=ZarinPalService())

        try:
            # همگام‌سازی کامل با آرگومان‌های تعبیه شده در بدنه متد سرویس شما
            result = service.verify_payment(
                authority=authority,
                callback_payload=request.data,
                payer_ip=payer_ip
            )

            return Response(result, status=drf_status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=drf_status.HTTP_400_BAD_REQUEST
            )


import ipaddress
import logging
from django.db import transaction
from rest_framework.views import APIView
from ..tasks import process_webhook

logger = logging.getLogger(__name__)

# لیست آی‌پی‌های معتبر یا رنج آی‌پی‌های زرین‌پال (این لیست را با مستندات آخر زرین‌پال مطابقت دهید)
ZARINPAL_VALID_IPS = [
    "185.143.232.0/24",  # نمونه رنج آی‌پی سرورهای زرین‌پال
    "127.0.0.1",         # برای تست‌های محلی (Local Development) - در پروداکشن حذف شود
]

def is_valid_zarinpal_ip(ip_string):
    """بررسی اینکه آیا آی‌پی درخواست‌کننده متعلق به زرین‌پال است یا خیر"""
    if not ip_string:
        return False
    try:
        request_ip = ipaddress.ip_address(ip_string)
        for valid_network in ZARINPAL_VALID_IPS:
            if "/" in valid_network:
                if request_ip in ipaddress.ip_network(valid_network, strict=False):
                    return True
            else:
                if request_ip == ipaddress.ip_address(valid_network):
                    return True
    except ValueError:
        return False
    return False


class ZarinpalWebhookView(APIView):
    # وب‌هوک نیازی به توکن کاربر فرانت ندارد، اما لایه‌های امنیتی زیر جایگزین آن می‌شوند
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # لایه امنیتی ۱: بررسی معتبر بودن آی‌پی فرستنده (جلوگیری از جعل فرانت/هکر)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR", "")

        if not is_valid_zarinpal_ip(client_ip):
            logger.warning(f"جعل احتمالی وب‌هوک! درخواست مشکوک از آی‌پی غیرمجاز: {client_ip}")
            # بازگرداندن پاسخ گمراه‌کننده یا ۴۰۳ صریح به هکر
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        authority = serializer.validated_data["authority"]

        # لایه امنیتی ۲: قفل اتمیک برای جلوگیری از پردازش همزمان وب‌هوک و دکمه بازگشت کاربر
        with transaction.atomic():
            payment = (
                PaymentSession.objects
                .select_for_update()
                .filter(authority=authority)
                .first()
            )

            if not payment:
                return Response({"detail": "invalid authority"}, status=status.HTTP_400_BAD_REQUEST)

            if payment.is_verified:
                # اگر کاربر قبلاً خودش با دکمه بازگشت پرداخت را تایید کرده، به گیت‌وی ۲۰۰ می‌دهیم تا دیگر وب‌هوک نفرستد
                return Response({"detail": "already verified"}, status=status.HTTP_200_OK)

            # ثبت رویداد خام وب‌هوک همراه با لینک مستقیم به تراکنش مربوطه (حل باگ ارور سلری)
            event = WebhookEvent.objects.create(
                payment=payment,  # پاس دادن مستقیم آبجکت پرداخت به مدل وب‌هوک
                authority=authority,
                payload=request.data,
                headers=dict(request.headers),
                ip_address=client_ip,
            )

        # ارسال تسک به پس‌زمینه ورکر سلری خارج از بلاک تراکنش اتمیک دیتابیس
        transaction.on_commit(lambda: process_webhook.delay(str(event.uuid)))

        # گیت‌وی فقط منتظر تایید وضعیت اکشن است، سریعا پاسخ ok می‌دهیم تا تایم‌اوت نخورد
        return Response({"ok": True}, status=status.HTTP_200_OK)


from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

class RefundMoneyToAccount(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PaymentService(zarinpal_client=ZarinPalService())

        try:
            result = service.withdraw_to_bank(
                user=request.user,
                amount=serializer.validated_data["amount"],
                deposit_payment_uuid=serializer.validated_data["deposit_payment_uuid"],
                method=serializer.validated_data["method"],
                request=request,
            )

            return Response(result, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )