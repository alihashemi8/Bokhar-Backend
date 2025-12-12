from django.urls import path

from . import views
from .views import *

app_name = "users"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("verify/", views.VerifyTokenView.as_view(), name="verify"),
    path("resend-otp/", views.resend_otp, name="resend-otp"),
    path("verify-otp/", views.verify_otp, name="verify-otp"),
    path("logout/", views.LogOutView.as_view(), name="logout"),
]
