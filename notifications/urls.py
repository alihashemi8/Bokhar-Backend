from django.urls import include, path

from .notif_urls import *

app_name = "notif"

urlpatterns = [
    path("", include("notifications.notif_urls.notif_urls")),
    path("", include("notifications.notif_urls.history_urls")),
    path("", include("notifications.notif_urls.send_sms_urls")),
]
