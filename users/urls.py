from django.urls import path
from users import views

urlpatterns = [
    path("submit/", views.submit),
    path("verify-otp/", views.verify_otp),
    path("resend-otp/", views.resend_otp),
]
