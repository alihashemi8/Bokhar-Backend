from rest_framework import serializers
from django.db import transaction
from order.models import *
from discounts.models import *
#from wallet.models.models import *


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # همه‌ی فیلدهای سریالایزر را فقط خواندنی کن
        for field in self.fields.values():
            field.read_only = True


class HistoryOrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"
        # نیازی به read_only_fields نیست

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # همه‌ی فیلدهای سریالایزر را فقط خواندنی کن
        for field in self.fields.values():
            field.read_only = True


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = transaction
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # همه‌ی فیلدهای سریالایزر را فقط خواندنی کن
        for field in self.fields.values():
            field.read_only = True


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # همه‌ی فیلدهای سریالایزر را فقط خواندنی کن
        for field in self.fields.values():
            field.read_only = True


class GlobalDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalDiscount
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # همه‌ی فیلدهای سریالایزر را فقط خواندنی کن
        for field in self.fields.values():
            field.read_only = True


from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from products.models import *
from  users.models import *

from .models import NotificationForAdvertising, NotificationForLate, SmsLog


class SmsLogSerializer(serializers.ModelSerializer):
    # فیلدهای GenericForeignKey به‌صورت دستی مدیریت می‌شوند
    content_type = serializers.SlugRelatedField(
        slug_field="model",
        queryset=ContentType.objects.all(),
        required=False,
        allow_null=True,
    )
    object_id = serializers.IntegerField(required=False, allow_null=True)
    related_object_repr = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SmsLog
        fields = [
            "id",
            "phone_number",
            "message",
            "sms_type",
            "status",
            "sent_at",
            "provider_response",
            "content_type",
            "object_id",
            "related_object_repr",
            "created_at",
        ]
        read_only_fields = ["status", "sent_at", "created_at", "related_object_repr"]

    def get_related_object_repr(self, obj):
        if obj.related_object:
            return str(obj.related_object)
        return None

    def create(self, validated_data):
        # اگر content_type و object_id ارائه شوند، شیء مرتبط تنظیم می‌شود
        # اما GenericForeignKey به‌صورت مستقیم در create ست نمی‌شود؛
        # باید با استفاده از متدهای خود شیء مدیریت شود.
        # در اینجا برای سادگی آن‌ها را به مدل می‌دهیم.
        return super().create(validated_data)


class NotificationForAdvertisingSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )
    product_pricing = serializers.PrimaryKeyRelatedField(
        queryset=ProductPricingTab.objects.all(), many=True, required=False
    )

    class Meta:
        model = NotificationForAdvertising
        fields = [
            "id",
            "created_by",
            "product_pricing",
            "title",
            "message",
            "brand",
            "link",
            "create_time",
            "month_key",
            "status",
        ]
        read_only_fields = [
            "create_time",
            "month_key",
            "status",
        ]  # status by default 'success' but maybe admin sets it

    # در NotificationForAdvertisingSerializer
    def validate(self, data):
        user = data.get("created_by") or self.context["request"].user
        now = timezone.now()
        month_key = f"{now.year:04d}-{now.month:02d}"
        # بررسی وجود یک اعلان با همین کاربر و ماه
        exists = NotificationForAdvertising.objects.filter(
            created_by=user, month_key=month_key
        ).exists()
        if self.instance:  # در حالت به‌روزرسانی، خودش را در نظر نگیریم
            exists = exists.exclude(pk=self.instance.pk)
        if exists:
            raise serializers.ValidationError(
                "شما قبلاً در این ماه یک اعلان تبلیغاتی ثبت کرده‌اید."
            )
        return data


class NotificationForLateSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = NotificationForLate
        fields = [
            "id",
            "title",
            "message",
            "user",
            "created_by",
            "status",
            "create_time",
        ]
        read_only_fields = ["create_time", "status"]
