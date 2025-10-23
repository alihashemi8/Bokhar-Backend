from django.urls import path
from . import views

app_name = "users"  

urlpatterns = [
    path("submit/", views.submit_otp, name="submit-otp"),
    path("resend-otp/", views.resend_otp, name="resend-otp"),
    path("verify-otp/", views.verify_otp, name="verify-otp"),
    path("register/", views.register_user, name="register"),
    path("login/", views.login_user, name="login"),
    path("check-auth/", views.check_auth, name="check-auth"),
    path("logout/", views.logout_user, name="logout"),
    path("me/", views.get_me, name="me"),
]
