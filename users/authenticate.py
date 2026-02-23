from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_access = request.COOKIES.get("access")
        raw_refresh = request.COOKIES.get("refresh")

        if not raw_access:
            return None

        try:
            validated_access = self.get_validated_token(raw_access)
        except TokenError:
            # AccessToken منقضی شده
            return None

        # بررسی blacklist روی refresh
        if raw_refresh:
            try:
                refresh_token = RefreshToken(raw_refresh)
                if getattr(refresh_token, "blacklisted", False):
                    return None
            except TokenError:
                return None

        return self.get_user(validated_access), validated_access


User = get_user_model()

class CustomBackend(ModelBackend):
    def authenticate(self, request, phone=None, password=None, **kwargs):
        if not phone or not password:
            return None

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
