from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("resend-otp/", views.resend_otp, name="resend-otp"),
    path("verify-otp/", views.verify_otp, name="verify-otp"),

    path("logout/", views.LogOutView.as_view(), name="logout"),

    path("logout1/", views.logout_user, name="logout"),

]
