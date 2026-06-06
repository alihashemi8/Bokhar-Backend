from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import generics, status
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


class PaymentTerminalListCreateView(generics.ListCreateAPIView):
    """
    لیست درگاه‌های کاربر و ایجاد درگاه جدید
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # هر کاربر فقط درگاه‌های خود را ببیند
        return PaymentTerminal.objects.filter(owner=self.request.user, is_deleted=False)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PaymentTerminalCreateUpdateSerializer
        return PaymentTerminalListSerializer

    def perform_create(self, serializer):
        # اینجا می‌توان با زرین‌پال ثبت terminal کرد و terminal_id را گرفت،
        # اما فعلاً فرض می‌کنیم داده‌های اولیه از کلاینت می‌آید.
        # در صورت نیاز به فراخوانی API زرین‌پال:
        # client = get_zarinpal_client()
        # result = client.create_terminal(...)
        # terminal = serializer.save(owner=self.request.user, terminal_id=result['terminal_id'], raw_response=result)
        serializer.save(owner=self.request.user)


class PaymentTerminalDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    مشاهده، ویرایش و حذف یک درگاه
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentTerminal.objects.filter(owner=self.request.user, is_deleted=False)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return PaymentTerminalCreateUpdateSerializer
        return PaymentTerminalDetailSerializer

    def perform_destroy(self, instance):
        # حذف نرم
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()


from wallet.models.setting_payment_models import BankAccount
from wallet.serializers.setting_account_serializers import *


class BankAccountListCreateView(generics.ListCreateAPIView):
    """
    لیست حساب‌های بانکی کاربر و ثبت حساب جدید
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BankAccountDetailSerializer
        return BankAccountListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BankAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    مشاهده، ویرایش و حذف حساب بانکی
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return BankAccountDetailSerializer

    def perform_destroy(self, instance):
        # در صورت نیاز به حذف نرم، مشابه درگاه
        instance.delete()  # یا حذف نرم


from wallet.models.setting_payment_models import TerminalBankAccount


class TerminalBankAccountCreateView(generics.CreateAPIView):
    """
    اتصال یک حساب بانکی به درگاه
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TerminalBankAccountWriteSerializer

    def perform_create(self, serializer, id):
        terminal = PaymentTerminal.objects.get(
            id=id, owner=self.request.user, is_deleted=False
        )
        serializer.save(terminal=terminal)


class TerminalBankAccountUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    ویرایش یا حذف اتصال حساب به درگاه
    """

    permission_classes = [IsAuthenticated]
    queryset = TerminalBankAccount.objects.all()

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return TerminalBankAccountWriteSerializer
        return TerminalBankAccountReadSerializer

    def get_queryset(self):
        # فقط اتصالات مربوط به درگاه‌های کاربر
        return TerminalBankAccount.objects.filter(
            terminal__owner=self.request.user, terminal__is_deleted=False
        )


class SettlementTriggerView(APIView):
    """
    راه‌اندازی دستی تسویه روزانه برای یک درگاه مشخص
    """

    permission_classes = [IsAuthenticated]  # شاید بهتر باشد IsAdminUser

    def post(self, request, terminal_id):
        # فقط مالک درگاه یا ادمین بتواند تسویه را اجرا کند
        terminal = PaymentTerminal.objects.filter(
            id=terminal_id, owner=request.user, is_deleted=False
        ).first()
        if not terminal:
            return Response(
                {"detail": "درگاه یافت نشد یا متعلق به شما نیست."},
                status=status.HTTP_404_NOT_FOUND,
            )

        client = ZarinPalService()  # کلاینت زرین‌پال
        service = ZarinpalSettlementService(gateway_client=client)

        try:
            settlements = service.process_daily_settlement(terminal_id=terminal.id)
            # سریالایز کردن settlements برگشتی
            serializer = SettlementSerializer(settlements, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Settlement trigger failed: {e}")
            return Response(
                {"detail": "خطای داخلی در فرآیند تسویه."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SettlementListView(APIView):
    """
    لیست تسویه‌های انجام‌شده (فیلتر بر اساس درگاه)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SettlementSerializer

    def get(self, request, id):
        qs = Settlement.objects.filter(terminal__owner=self.request.user, id=id)
        serializer = SettlementSerializer(qs, many=True)
        return serializer.data
