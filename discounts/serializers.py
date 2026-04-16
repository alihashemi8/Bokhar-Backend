from rest_framework import serializers
from .models import ProductDiscount, GlobalDiscount, Coupon


class ProductDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDiscount
        fields = "__all__"


class GlobalDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalDiscount
        fields = "__all__"


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
