from django.urls import path
from . import views

urlpatterns = [
    path("submit/", views.submit_otp),
    path("verify/", views.verify_otp),
    path("resend/", views.resend_otp),
    path("register/", views.register_user),
    path("login/", views.login_user),
    path("check-auth/", views.check_auth),
    path("logout/", views.logout_user),
    path("me/", views.get_me),
]
