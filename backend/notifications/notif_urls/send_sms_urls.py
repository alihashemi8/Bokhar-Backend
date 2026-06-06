# notification/report_urls.py
from django.urls import path

from ..discount_sms_views import *

urlpatterns = [
    path("coupon/<int:id>/", CouponToCustomer.as_view(), name="coupon-send-sms"),
    path(
        "global-discount/<int:id>/",
        GlobalToCustomer.as_view(),
        name="global-discount-send-sms",
    ),
]
