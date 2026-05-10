from rest_framework import serializers

class WalletChargeSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=100000)
    def validate_amount(self, data):
        if  data < 100000:
            raise serializers.ValidationError("حداقل مبلغ شارژ 100000 تومان است")
        return data



class WalletVerifySerializer(serializers.Serializer):
    """سریالایزر تایید پرداخت"""
    authority = serializers.CharField()
    status = serializers.CharField()