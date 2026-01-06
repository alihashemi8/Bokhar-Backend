# Create your views here.
import uuid

from django.db import transaction
from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# wallet/views.py
from rest_framework.views import APIView

from .models import *
from .serializer import *
from .utils import *

# Create your views here.


class IncreaseWalletView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = IncreaseBalanceWalletSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        txn = WalletTransaction.objects.create(
            wallet=wallet,
            type=WalletType.Deposite,
            status=WalletStatus.Pending,
            created_at=timezone.now(),
            amount=amount,
            reference=str(uuid.uuid4()),
            purpose=WalletTransaction.WALLET_CHARGE,
        )
        # payment_url = f"https://zarinpal.com/pay/{txn.reference}"
        return Response({"detail": "پرداخت آنلاین"}, status=status.HTTP_200_OK)


class PayOrderWithWalletView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        amount = 0
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        balance = get_balance(wallet.id)

        if balance < amount:
            return Response("موجودی کافی نیست وارد درگاه پرداخت شوید.")

        else:
            # پرداخت مستقیم از کیف پول
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                txn = WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=-order.amount,
                    type=WalletTransaction.WITHDRAW,
                    reference=str(uuid.uuid4()),
                    status="SUCCESS",
                    purpose=WalletTransaction.WALLET_CHARGE,
                )
                update_balance(wallet.id, amount)
                return Response(
                    {"detail": "پرداخت با کیف پول موفق", "transaction": txn.reference}
                )


class PayOrder(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        amount = 0
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        txn = WalletTransaction.objects.create(
            wallet=wallet,
            type=WalletType.Withdraw,
            status=WalletStatus.Pending,
            created_at=timezone.now(),
            amount=amount,
            reference=str(uuid.uuid4()),
            purpose=WalletTransaction.ORDER_PAYMENT,
        )
        # payment_url = f"https://zarinpal.com/pay/{txn.reference}"
        return Response({"detail": "پرداخت آنلاین"})


class ZarinpalVerifyView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        ref_id = request.data.get("Authority")
        wallet_txn = WalletTransaction.objects.filter(reference=ref_id).first()
        if wallet_txn.purpose != WalletTransaction.WALLET_CHARGE:
            update_balance(wallet_txn.wallet.id, wallet_txn.amount)
            wallet_txn.status = WalletTransaction.SUCCESS
            wallet_txn.save()
        else:
            wallet_txn.status = WalletTransaction.SUCCESS
            wallet_txn.save()
        return Response(status=status.HTTP_200_OK)


class DetailWalletView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)
