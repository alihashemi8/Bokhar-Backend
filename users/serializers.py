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
    class Meta:
        model = User
        fields = ["fullname", "phone", "id"]


# ------------------------
# Send OTP
# ------------------------
class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)

    def validate(self, attrs):
        phone = attrs["phone"]
        can_send, remaining = can_send_otp(phone)

        if not can_send:
            minutes, seconds = safe_divmod(remaining)
            raise serializers.ValidationError(
                {
                    "پیام": f"شما بیش از حد درخواست دادید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                }
            )

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
            raise serializers.ValidationError(
                {"phone": "شماره تلفن باید ۱۱ رقم باشد"}
            )

        blocked, remaining = is_phone_blocked(phone)
        if blocked:
            minutes, seconds = safe_divmod(remaining)
            raise serializers.ValidationError(
                {
                    "پیام": f"شما بیش از حد درخواست دادید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                }
            )

        if not verify_otp(phone, otp):
            blocked, remaining = register_failed_attempt(phone)
            if blocked:
                minutes, seconds = safe_divmod(remaining)
                raise serializers.ValidationError(
                    {
                        "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                    }
                )
            raise serializers.ValidationError(
                {"otp": "کد وارد شده اشتباه است"}
            )

        cache.delete(f"otp_fail:{phone}")
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
            raise serializers.ValidationError(
                {"پیام": "شماره اشتباه است یا ثبت‌نام نکرده‌اید"}
            )

        blocked, remaining = is_phone_blocked(phone)
        if blocked:
            minutes, seconds = safe_divmod(remaining)
            raise serializers.ValidationError(
                {
                    "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                }
            )

        if not verify_otp(phone, otp):
            blocked, remaining = register_failed_attempt(phone)
            if blocked:
                minutes, seconds = safe_divmod(remaining)
                raise serializers.ValidationError(
                    {
                        "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                    }
                )
            raise serializers.ValidationError(
                {"otp": "کد وارد شده اشتباه است"}
            )

        cache.delete(f"otp_fail:{phone}")
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

        if len(password) < 6:
            raise serializers.ValidationError(
                {"password": "حداقل طول رمز عبور ۶ کاراکتر است"}
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
