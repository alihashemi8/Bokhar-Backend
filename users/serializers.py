import re

from django.contrib.auth import authenticate
from django.core.cache import cache
from rest_framework import serializers

from .models import User
from .utils import (
    can_send_otp,
    is_phone_blocked,
    verify_otp,
    register_failed_attempt,
)


# ------------------------
# Helper
# ------------------------
def safe_divmod(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        seconds = 0
    return divmod(seconds, 60)


# ------------------------
# User
# ------------------------
class UserSerializer(serializers.ModelSerializer):
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "fullname", "phone", "has_password"]

    def get_has_password(self, obj):
        return obj.has_usable_password()




# ------------------------
# Send OTP
# ------------------------
class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)

    def validate(self, attrs):
        phone = attrs["phone"]
        can_send, message_or_remaining = can_send_otp(phone)

        if not can_send:
            # message_or_remaining در اینجا رشته‌ای مثل "شماره بلاک است..." است
            # اگر می‌خواهید دقیقاً مثل قبل دقیقه/ثانیه نمایش دهید، باید منطق را تغییر دهید
            # یا اینکه از is_phone_blocked جداگانه استفاده کنید
            raise serializers.ValidationError({"پیام": message_or_remaining})

        return attrs



# ------------------------
# Register with OTP
# ------------------------
class RegisterOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    fullname = serializers.CharField()
    otp = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get("phone")
        otp = attrs.get("otp")

        if not phone or len(phone) != 11:
            raise serializers.ValidationError({"phone": "شماره تلفن باید ۱۱ رقم باشد"})

        # چک بلاک بودن
        blocked, remaining = is_phone_blocked(phone)
        if blocked:
            minutes, seconds = safe_divmod(remaining)
            raise serializers.ValidationError({
                "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
            })

        # بررسی OTP - توجه به unpack کردن تاپل
        is_valid, message = verify_otp(phone, otp)
        if not is_valid:
            # message می‌تواند "کد اشتباه است" یا "شماره بلاک است" یا "منقضی شده" باشد
            raise serializers.ValidationError({"otp": message})

        # موفق: verify_otp خودش cache.delete_many کرده
        return attrs

    def create(self, validated_data):
        phone = validated_data["phone"]

        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError(
                {"پیام": "قبلاً ثبت‌نام کرده‌اید"}
            )

        user = User.objects.create_user(
            phone=phone,
            fullname=validated_data["fullname"],
        )
        return user


# ------------------------
# Login with OTP
# ------------------------
class LoginOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        otp = attrs.get("otp")

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError({"پیام": "شماره اشتباه است یا ثبت‌نام نکرده‌اید"})

        blocked, remaining = is_phone_blocked(phone)
        if blocked:
            minutes, seconds = safe_divmod(remaining)
            raise serializers.ValidationError({
                "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
            })

        is_valid, message = verify_otp(phone, otp)
        if not is_valid:
            raise serializers.ValidationError({"otp": message})

        attrs["user"] = user
        return attrs



# ------------------------
# Login with Password
# ------------------------
class LoginPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

        user = authenticate(phone=phone, password=password)
        if user is None:
            raise serializers.ValidationError(
                {"پیام": "رمز عبور یا شماره تلفن اشتباه است"}
            )

        attrs["user"] = user
        return attrs


# ------------------------
# Edit Fullname
# ------------------------
class EditFullNameSerializer(serializers.Serializer):
    fullname = serializers.CharField()

    def update(self, instance, validated_data):
        instance.fullname = validated_data["fullname"]
        instance.save()
        return instance


# ------------------------
# Edit Password
# ------------------------
class EditPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        password = attrs.get("password")

        if user.has_usable_password():
            if not attrs.get("old_password"):
                raise serializers.ValidationError(
                    {"old_password": "رمز عبور فعلی را وارد کنید"}
                )
            if not user.check_password(attrs["old_password"]):
                raise serializers.ValidationError(
                    {"old_password": "رمز عبور فعلی اشتباه است"}
                )

        if len(password) < 8:
            raise serializers.ValidationError(
                {"password": "حداقل طول رمز عبور 8 کاراکتر است"}
            )

        rules = [
            re.search(r"\d", password),
            re.search(r"[A-Z]", password),
            re.search(r"[a-z]", password),
        ]
        if not all(rules):
            raise serializers.ValidationError(
                {"password": "رمز باید شامل حروف بزرگ، کوچک و عدد باشد"}
            )

        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "رمز عبور و تکرار آن یکسان نیست"}
            )

        return attrs

    def update(self, instance, validated_data):
        instance.set_password(validated_data["password"])
        instance.save()
        return instance

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "fullname",
            "phone",
            "created_at",
        ]
