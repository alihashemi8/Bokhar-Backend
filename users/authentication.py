from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

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
