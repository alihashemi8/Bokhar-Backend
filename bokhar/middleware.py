
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)

class CookieToHeaderMiddleware(MiddlewareMixin):


    def process_request(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header:
            return None

        try:
            cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "access")
            token = request.COOKIES.get(cookie_name)
            if token:
                request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        except Exception as e:
            if settings.DEBUG:
                logger.warning(f"CookieToHeaderMiddleware error: {e}")

        return None
