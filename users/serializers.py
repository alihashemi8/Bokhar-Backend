import re

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User
from .utils import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["fullname", "phone", "id"]


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)

    def validate(self, attrs):
        phone = attrs["phone"]
        can_send, remaining = can_send_otp(phone)

        if not can_send:
            minutes, seconds = divmod(remaining, 60)
            raise serializers.ValidationError(
                {
                    "پیام": f"شما بیش از حد درخواست دادید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                }
            )

        return attrs


# OTP
class RegisterOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    fullname = serializers.CharField()
    otp = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get("phone")
        otp = attrs.get("otp")

        # اعتبار شماره
        if not phone or len(phone) != 11:
            raise serializers.ValidationError({"phone": "شماره تلفن باید ۱۱ رقم باشد"})

        # بررسی بلاک بودن
        blocked, remaining = is_phone_blocked(phone)
        if blocked:
            minutes, seconds = divmod(remaining, 60)
            raise serializers.ValidationError(
                {
                    "پیام": f"شما بیش از حد درخواست دادید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                }
            )

        # بررسی OTP
        if not verify_otp(phone, otp):
            blocked, remaining = register_failed_attempt(phone)
            if blocked:
                minutes, seconds = divmod(remaining, 60)
                raise serializers.ValidationError(
                    {
                        "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                    }
                )
            raise serializers.ValidationError({"otp": "کد وارد شده اشتباه است"})

        cache.delete(f"otp_fail:{phone}")
        return attrs

    def create(self, validated_data):
        phone = validated_data.get("phone")
        user = User.objects.filter(phone=phone)
        if user.exists():
            raise serializers.ValidationError({"پیام": "قبلا ثبت نام کرده ای"})
        user = User.objects.create_user(
            phone=phone,
            fullname=validated_data["fullname"],
        )
        return user


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
                {"پیام": "شماره اشتباه است یا ثبت نام نکردی"}
            )

        # بررسی بلاک بودن
        blocked, remaining = is_phone_blocked(phone)
        if blocked:
            minutes, seconds = divmod(remaining, 60)
            raise serializers.ValidationError(
                {
                    "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                }
            )

        # بررسی OTP
        if not verify_otp(phone, otp):
            blocked, remaining = register_failed_attempt(phone)
            if blocked:
                minutes, seconds = divmod(remaining, 60)
                raise serializers.ValidationError(
                    {
                        "پیام": f"شما بیش از حد تلاش کردید. لطفاً {minutes} دقیقه و {seconds} ثانیه صبر کنید."
                    }
                )
            raise serializers.ValidationError({"otp": "کد وارد شده اشتباه است"})

        attrs["user"] = user
        cache.delete(f"otp_fail:{phone}")
        return attrs


class LoginPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")
        # request = self.context.get("request")  # مهم!
        print("phone", phone, "pass", password)
        user = authenticate(phone=phone, password=password)
        if user is None:
            raise serializers.ValidationError(
                {"پیام": "رمز عبور یا شماره تلفن اشتباه است"}
            )
        else:
            attrs["user"] = user
        return attrs


class EditFullNameSerializer(serializers.Serializer):
    fullname = serializers.CharField()

    def update(self, instance, validated_data):
        instance.fullname = validated_data.get("fullname")
        instance.save()
        return instance


class EditPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

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
            raise serializers.ValidationError({"password": "حداقل طول رمز 6 حرف است"})

        rules = [
            re.search(r"\d", password),
            re.search(r"[A-Z]", password),
            re.search(r"[a-z]", password),
        ]
        if not all(rules):
            raise serializers.ValidationError(
                {"password": "رمز حداقل 1 حروف بزرگ و کوچک و حداقل 1 عدد"}
            )

        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError(
                {"password2": "رمز عبور و تکرار آن یکسان نیست"}
            )

        return attrs

    def update(self, instance, validated_data):
        instance.set_password(validated_data["password"])
        instance.save()
        return instance


