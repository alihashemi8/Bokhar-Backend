from rest_framework import serializers

from .models import *
from .utils import *


class WalletTransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = WalletTransaction
        fields = ["amount", "type", "status", "reference", "created_at"]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(
        many=True, read_only=True
    )  #  اینجا رابطه ForeignKey استفاده شد
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ["user", "transactions", "balance"]

    def get_balance(self, obj):
        return get_balance(obj.id)


class IncreaseBalanceWalletSerializer(serializers.ModelSerializer):

    class Meta:
        model = WalletTransaction
        fields = ["amount", "type", "status", "reference", "created_at"]
        read_only_fields = ["type", "status", "reference", "created_at"]

    def validate(self, attrs):
        amount = attrs["amount"]
        if amount <= 0:
            raise serializers.ValidationError("افزایش موجودی مقداری مثبت باشد.")

        return attrs
