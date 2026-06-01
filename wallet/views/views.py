# Create your views here.
from math import gamma

from django.urls import reverse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from order.models import *
from order.session import *
from wallet.models.models import *
from wallet.models.setting_payment_models import *
from wallet.serializers.serializers import *
from wallet.serializers.setting_account_serializers import *
from wallet.services.service_zarinpal import *
from wallet.services.services_account_settlement import *
from wallet.services.services_payment import *
from wallet.services.services_wallet import *


class WalletPayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = OrderSession(request)
        user = request.user
        data = request.data
        idempotency_key = request.data.get("idempotency_key", str(uuid.uuid4()))
        service = WalletPaymentService(gateway=ZarinPalService())
        try:
            result = service.pay_with_wallet(
                user=user,
                cart=cart,  # آبجکت‌های CartItem به صورت queryset
                validated_data=data,  # اطلاعات سفارش (آدرس، زمان و غیره)
                request=request,
                idempotency_key=idempotency_key,
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


from django.urls import reverse


class WalletChargeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        # دریافت ترمینال فعال (از PaymentCreateSerializer می‌توان terminal_id گرفت)
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

        # ساخت آدرس کال‌بک
        callback_url = request.build_absolute_uri(
            reverse("payment-verify")  # نام url مربوط به ویو PaymentVerifyView
        )
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
        status = serializer.validated_data["status"]
        service = WalletPaymentService(gateway=ZarinPalService())
        try:
            result = service.verify_wallet_charge(
                request=request,
                authority=authority,
                status=status,
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RefundOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        user = request.user

        try:
            order = Order.objects.get(id=id, status="paid")

        except Order.DoesNotExist:
            return Response(
                {"detail": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND
            )

        service = WalletPaymentService(gateway=ZarinPalService())
        try:
            updated_order = service.refund_to_wallet(
                order=order,
            )
            return Response(
                {
                    "detail": "بازگشت وجه با موفقیت انجام شد.",
                    "order_id": updated_order.id,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# برای درگاه پرداخت


class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = OrderSession(request)
        # دریافت ترمینال فعال (از PaymentCreateSerializer می‌توان terminal_id گرفت)
        terminal_id = serializer.validated_data["terminal_id"]
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

        service = PaymentService(zarinpal_client=ZarinPalService())
        try:
            result = service.initiate_payment(
                user=request.user,
                cart=cart,
                data=request.data,
                terminal=terminal,
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        authority = serializer.validated_data["authority"]
        status = serializer.validated_data["status"]

        service = PaymentService(zarinpal_client=ZarinPalService())
        try:
            result = service.verify_payment(
                request=request,
                authority=authority,
                status=status,
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RefundMoneyToAccount(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # ۱. اعتبارسنجی فیلدهای موجود در سریالایزر (amount و bank_name)
        serializer = WithdrawalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = PaymentService(ZarinPalService())
        # ۲. دریافت deposit_payment_uuid (اجباری در سرویس)
        deposit_payment_uuid = serializer.validated_data.get("deposit_payment_uuid")
        if not deposit_payment_uuid:
            return Response(
                {"detail": "شناسه تراکنش شارژ (deposit_payment_uuid) الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ۳. دریافت method با اعتبارسنجی دستی
        method = serializer.validated_data.get("method", "CARD").upper()
        if method not in ["CARD", "PAYA"]:
            return Response(
                {"detail": "روش برداشت نامعتبر است. مقادیر مجاز: CARD یا PAYA"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ۴. فراخوانی سرویس
        try:
            result = service.withdraw_to_bank(
                user=request.user,
                amount=serializer.validated_data["amount"],
                deposit_payment_uuid=deposit_payment_uuid,
                method=method,
                request=request,
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
