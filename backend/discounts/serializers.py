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
        fields = [
            'id', 'code', 'type', 'value', 'user',
            'usage_limit', 'used_count', 'min_order_amount',
            'starts_at', 'ends_at', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'used_count']
        # اگر می‌خواهید کد توسط بک‌اند ساخته شود و فرستاده شود:
        extra_kwargs = {
            'code': {'required': False, 'allow_blank': True}
        }

