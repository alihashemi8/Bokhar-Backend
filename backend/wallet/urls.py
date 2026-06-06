from django.urls import include, path

from .urls_wallet import *

app_name = "walllet"

urlpatterns = [
    path("", include("backend.wallet.urls_wallet.admin_urls")),
    path("", include("backend.wallet.urls_wallet.payment_urls")),
]
