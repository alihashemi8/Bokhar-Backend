from rest_framework import serializers
from .models import ProductDiscount, GlobalDiscount, Coupon


class ProductDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDiscount
        fields = "__all__"

    def validate(self, data):
        if not data.get("material"):
            raise serializers.ValidationError(
                "تخفیف فقط باید روی جنس اعمال شود"
            )
        return data


class GlobalDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalDiscount
        fields = "__all__"


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"