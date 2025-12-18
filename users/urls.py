from django.urls import path

from . import views
from .views import *

app_name = "users"

urlpatterns = [
    path("sent/otp", views.SendOTPView.as_view(), name="otp"),
    path("register/otp", views.RegisterOTPView.as_view(), name="register"),
    path("login/otp", views.LoginOTPView.as_view(), name="login_otp"),
    path("login/", views.LoginPasswordView.as_view(), name="login"),
    path("edit/name", views.EditFullNameView.as_view(), name="fullname"),
    path("edit/password", views.EditPasswordView.as_view(), name="password"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("verify/", views.VerifyTokenView.as_view(), name="verify"),
    path("logout/", views.LogOutView.as_view(), name="logout"),
]
