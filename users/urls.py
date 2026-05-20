from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    SendOTPView,
    RegisterOTPView,
    LoginOTPView,
    LoginPasswordView,
    EditFullNameView,
    EditPasswordView,
    RefreshTokenView,
    VerifyTokenView,
    LogOutView,
     VerifyOTPView,
    CustomerViewSet,
    get_csrf_token,
)

app_name = "users"

urlpatterns = [
    path("send/otp/", SendOTPView.as_view(), name="otp"),
    path("verify/otp/", VerifyOTPView.as_view(), name="verify-otp"),  
    path("register/otp/", RegisterOTPView.as_view(), name="register"),
    path("login/otp/", LoginOTPView.as_view(), name="login_otp"),
    path("login/", LoginPasswordView.as_view(), name="login"),
    path("edit/name/", EditFullNameView.as_view(), name="fullname"),
    path("edit/password/", EditPasswordView.as_view(), name="password"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("verify/", VerifyTokenView.as_view(), name="verify"),
    path("logout/", LogOutView.as_view(), name="logout"),
    path("csrf/", get_csrf_token, name="get-csrf-token"),
]

# ------------------------------------------------------------------
# Router
# ------------------------------------------------------------------

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customers")

urlpatterns += router.urls
