from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404


class TerminalBankAccountCreateView(generics.CreateAPIView):
    """
    اتصال یک حساب بانکی به درگاه
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TerminalBankAccountWriteSerializer

    def perform_create(self, serializer):
        # دریافت شناسه ترمینال از پارامترهای URL (مثلاً /terminals/<id>/accounts/)
        terminal_id = self.kwargs.get("id")
        terminal = get_object_or_404(
            PaymentTerminal, id=terminal_id, owner=self.request.user, is_deleted=False
        )
        serializer.save(terminal=terminal)


class SettlementListView(APIView):
    """
    لیست تسویه‌های انجام‌شده مربوط به درگاه‌های کاربر
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        # فیلتر تسویه‌ها بر اساس شناسه‌ای که کاربر فرستاده، مشروط بر اینکه ترمینال مال خودش باشد
        qs = Settlement.objects.filter(terminal__owner=request.user, terminal_id=id)
        serializer = SettlementSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SettlementTriggerView(APIView):
    """
    راه‌اندازی دستی تسویه روزانه برای یک درگاه مشخص
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, terminal_id):
        terminal = get_object_or_404(
            PaymentTerminal, id=terminal_id, owner=request.user, is_deleted=False
        )

        client = ZarinPalService()
        service = ZarinpalSettlementService(gateway_client=client)

        try:
            settlements = service.process_daily_settlement(terminal_id=terminal.id)
            if not settlements:
                return Response({"detail": "مبلغی برای تسویه وجود نداشت یا تسویه قبلاً انجام شده است."},
                                status=status.HTTP_200_OK)

            serializer = SettlementSerializer(settlements, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, 'message') else e)},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Settlement trigger failed: {e}")
            return Response({"detail": "خطای داخلی در فرآیند تسویه."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

